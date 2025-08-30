from fastapi.responses import JSONResponse
from fastapi import Depends, APIRouter, BackgroundTasks, HTTPException, Request
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Dict
import time
import logging

from requests import Session

from config.settings import settings
from config.database import get_db
from schemas.chat import EnhancedChatRequest, EnhancedChatResponse
from schemas.errors import ValidationErrorResponse
from chain.loader import vectorstore
from chain.retriever import enhanced_retriever, query_processor
from tools.tool import ALL_TOOLS
from redis_cache.redis_cache import cache
from services.cost_tracking_callback_service import CostTrackingCallback

logger = logging.getLogger(__name__)

router = APIRouter()

ENHANCED_LEGAL_PROMPT = """You are an expert AI Legal Assistant specializing in Indian law. Your role is to:

1. Provide accurate, well-cited answers based on retrieved legal documents
2. Use available tools when additional research is needed
3. Adjust explanation complexity: {complexity_level}
4. Always include proper citations and sources
5. State confidence level and limitations clearly

Query Analysis: {query_analysis}

Retrieved Context:
{context}

Guidelines:
- Base answers primarily on retrieved documents
- Use tools for additional research when context is insufficient
- Provide confidence scoring based on source quality
- Include specific section/case references
- Recommend human legal consultation for complex matters

IMPORTANT: Format your response in HTML with the following structure:
- Use <h3> for main headings
- Use <h4> for sub-headings
- Use <p> for paragraphs
- Use <ul> and <li> for lists
- Use <strong> for important terms
- Use <em> for emphasis
- Use <blockquote> for quotes from legal documents
- Use <br> for line breaks where needed
- Include citations as <cite>Source Name, Section X</cite>

Answer the user's question comprehensively using the above context in HTML format.
"""

@router.post("/enhanced-chat", response_model=EnhancedChatResponse)
async def enhanced_chat(
    request: EnhancedChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)):
    start_time = time.time()

    try:
        # Step 1: Check cache first
        cache_key = f"{request.question}_{request.complexity_level}_{str(request.filters)}"
        cached_response = cache.get_cached_query(cache_key)

        if cached_response:
            logger.info(f"Cache hit for query: {request.question}")
            cached_response["response_time_ms"] = int((time.time() - start_time) * 1000)
            cached_response["from_cache"] = True
            return EnhancedChatResponse(**cached_response)

        # Step 2: Process and analyze query
        query_analysis = query_processor.preprocess_query(request.question)
        print(f"Query Analysis: {query_analysis}")


        # Step 4: Enhanced retrieval
        if request.use_hybrid_search and enhanced_retriever:
            # Use hybrid retriever with filters
            filters = request.filters or query_analysis.get('filters', {})
            relevant_docs = enhanced_retriever.retrieve_with_filters(
                query=request.question,
                filters=filters,
                k=5
        )
        else:
            # Fallback to basic retrieval
            retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
            relevant_docs = retriever.get_relevant_documents(request.question)

        # Step 5: Calculate confidence based on retrieval quality
        confidence = calculate_confidence(relevant_docs, query_analysis)

        # Step 6: Prepare context for LLM
        context = format_context(relevant_docs)

        # Step 7: Use LLM to generate answer
        llm = ChatOpenAI(temperature=0, model="gpt-4o-mini", openai_api_key=settings.openai_api_key)

        if request.use_tools and confidence < 0.7:
            print(f"Confidence low ({confidence:.2f}), using tools.")
            # Use tools when confidence is low
            prompt = ChatPromptTemplate.from_messages([
                ("system", ENHANCED_LEGAL_PROMPT),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}")
            ])
            agent = create_openai_tools_agent(
                llm=llm,
                tools=ALL_TOOLS,
                prompt=prompt,
            )

            cost_callback = CostTrackingCallback(user_id=request.user_id)
     
            agent_executor = AgentExecutor(
                agent=agent,
                tools=ALL_TOOLS,
                verbose=True,
                callbacks=[cost_callback]
            )
            result = agent_executor.invoke({
                "input": request.question,
                "query_analysis": str(query_analysis),
                "context": context,
                "complexity_level": request.complexity_level
            })
            answer = result['output']
            tools_used = [tool.name for tool in ALL_TOOLS]
        else:
            print(f"Confidence high ({confidence:.2f}), skipping tools.")
            # Use direct LLM with context
            prompt = ENHANCED_LEGAL_PROMPT.format(
                complexity_level=request.complexity_level,
                query_analysis=query_analysis,
                context=context
            )
            response = llm.invoke([
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": request.question
                }
            ])
            answer = response.content
            tools_used = []

        # Step 8: Format response
        response_time = int((time.time() - start_time) * 1000)
        
        # Extract citations from documents
        citations = extract_citations(relevant_docs)
        
        # Format source documents (avoid duplicates)
        formatted_sources = []
        seen_sources = set()
        
        for doc in relevant_docs:
            source_name = doc.metadata.get('source_file', 'Unknown')
            if source_name not in seen_sources:
                formatted_sources.append({
                    "source": source_name,
                    "page": doc.metadata.get('page', 'N/A'),
                    "document_type": doc.metadata.get('document_type', 'legal_document'),
                    "relevance_snippet": doc.page_content[:200] + "...",
                    "sections": doc.metadata.get('extracted_sections', []),
                    "legal_topics": doc.metadata.get('legal_topics', [])
                })
                seen_sources.add(source_name)

        response_data = {
            "answer": answer,
            "source_documents": formatted_sources,
            "confidence": confidence,
            "tools_used": tools_used,
            "citations": citations,
            "reading_level": request.complexity_level,
            "response_time_ms": response_time,
            "query_analysis": query_analysis,
            "retrieval_stats": {
                "documents_retrieved": len(relevant_docs),
                "unique_sources": len(set(doc.metadata.get('source_file') for doc in relevant_docs)),
                "average_relevance": confidence,
                "hybrid_search_used": request.use_hybrid_search and enhanced_retriever is not None
            },
            "from_cache": False
        }

        # cache the response for future use
        cache.set_cached_query(cache_key, response_data, expire=1800)
        return EnhancedChatResponse(**response_data)
    
    except ValueError as e:
        # Pydantic validation errors
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "VALIDATION_ERROR",
                "error_message": str(e)
            }
        )
    except Exception as e:
        logger.error(f"Enhanced chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "error_message": "An internal error occurred"
            }
        )
    
async def validation_exception_handler(request: Request, exc):
    """Handle validation errors with structured response."""
    logger.warning(f"Validation error on {request.url.path}: {exc}")
    
    return JSONResponse(
        status_code=422,
        content=ValidationErrorResponse(
            error_message="Request validation failed",
            details={"validation_errors": exc.detail if hasattr(exc, 'detail') else str(exc)}
        ).dict()
    )

def calculate_confidence(docs: List, query_analysis: Dict) -> float:
    """Calculate confidence score based on retrieval quality"""
    if not docs:
        return 0.1
    
    base_score = 0.6

    # Boost for exact section matches
    if query_analysis['sections']:
        section_matches = sum(
            1 for doc in docs 
            if any(section in doc.metadata.get('extracted_sections', []) 
                  for section in query_analysis['sections'])
        )
        base_score += (section_matches / len(docs)) * 0.2

     # Boost for act matches
    if query_analysis['acts']:
        act_matches = sum(
            1 for doc in docs
            if any(act in ' '.join(doc.metadata.get('extracted_acts', []))
                  for act in query_analysis['acts'])
        )
        base_score += (act_matches / len(docs)) * 0.15

    # Penalty for very short content
    avg_content_length = sum(len(doc.page_content) for doc in docs) / len(docs)
    if avg_content_length < 200:
        base_score -= 0.1

    return min(base_score, 0.95)  # Cap at 95%

def format_context(docs: List) -> str:
    """Format retrieved documents for LLM context"""
    context_parts = []
    
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get('source_file', 'Unknown')
        page = doc.metadata.get('page', 'N/A')
        doc_type = doc.metadata.get('document_type', 'legal_document')
        
        context_parts.append(
            f"Document {i} ({source}, Page {page}, Type: {doc_type}):\n"
            f"{doc.page_content}\n"
        )
    
    return "\n---\n".join(context_parts)

def extract_citations(docs: List) -> List[Dict]:
    """Extract structured citations from documents"""
    citations = []
    seen = set()
    
    for doc in docs:
        source = doc.metadata.get('source_file', 'Unknown')
        if source not in seen:
            citation = {
                "source": source,
                "type": doc.metadata.get('document_type', 'legal_document'),
                "sections": doc.metadata.get('extracted_sections', []),
                "acts": doc.metadata.get('extracted_acts', []),
                "page": doc.metadata.get('page', 'N/A')
            }
            citations.append(citation)
            seen.add(source)
    
    return citations