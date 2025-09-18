import json
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import Depends, APIRouter, BackgroundTasks, HTTPException, Request
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.callbacks.base import BaseCallbackHandler
from typing import List, Dict, Iterator, Any, AsyncGenerator
import time
import logging
from requests import Session
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from config.settings import settings
from config.database import get_db
from schemas.chat import EnhancedChatRequest, EnhancedChatResponse
from schemas.errors import ValidationErrorResponse
from chain.loader import vectorstore
from chain.retriever import enhanced_retriever, query_processor
from tools.tool import ALL_TOOLS
from redis_cache.redis_cache import cache
from services.cost_tracking_callback_service import CostTrackingCallback
from services.latency_tracking_service import latency_tracker
from services.latency_metric_service import LatencyMetricService
from services.auth_service import auth_service

logger = logging.getLogger(__name__)

router = APIRouter()

ENHANCED_LEGAL_PROMPT = """You are an expert AI Legal Assistant specializing in Indian law. Provide accurate, well-cited answers.

Complexity Level: {complexity_level}
Query Analysis: {query_analysis}

Retrieved Context:
{context}

Instructions:
- Base answers on retrieved documents
- Include proper citations and sources
- State confidence level and limitations
- Keep responses concise and focused

Format your response in HTML:
- Use <h3> for main headings
- Use <p> for paragraphs  
- Use <ul>/<li> for lists
- Use <strong> for important terms
- Include citations as 'Cite - Source Name, Section X' in italics
- Highlight key terms with color #d97706

Answer the user's question using the above context.
"""

EVAL_ALPHA = 0.75  # weight for retriever similarity
EVAL_BETA = 0.25   # weight for offline eval_score

try:
    raw_weights = cache.get("eval_rerank_weights")
    if raw_weights:
        parsed_weights = raw_weights if isinstance(raw_weights, dict) else json.loads(raw_weights)
        EVAL_ALPHA = float(parsed_weights.get("alpha", EVAL_ALPHA))
        EVAL_BETA = float(parsed_weights.get("beta", EVAL_BETA))
        logger.info("Loaded rerank weights from cache: alpha=%s beta=%s", EVAL_ALPHA, EVAL_BETA)
except Exception:
    logger.debug("No persisted rerank weights found or failed to load")

class StreamingCallbackHandler(BaseCallbackHandler):
    """Custom callback handler for streaming LLM responses"""
    
    def __init__(self):
        self.tokens = []
        self.is_streaming = True
    
    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Handle new token generation"""
        if self.is_streaming:
            self.tokens.append(token)
    
    def get_tokens(self) -> List[str]:
        """Get accumulated tokens"""
        return self.tokens
    
    def clear_tokens(self):
        """Clear accumulated tokens"""
        self.tokens.clear()

async def stream_response_generator(
    payload: EnhancedChatRequest,
    db: Session,
    request_id: str = None
) -> AsyncGenerator[str, None]:
    """
    Generator function for streaming chat responses
    """
    start_time = time.time()
    
    try:
        # Yield initial status
        yield f"data: {json.dumps({'type': 'status', 'message': 'Processing query...', 'timestamp': time.time()})}\n\n"
        
        # Step 1: Check cache first
        cache_key = f"{payload.question}_{payload.complexity_level}"
        cached_response = cache.get_cached_query(cache_key)
        
        if cached_response:
            # If cached, return immediately
            cached_response["response_time_ms"] = int((time.time() - start_time) * 1000)
            cached_response["from_cache"] = True
            
            yield f"data: {json.dumps({'type': 'complete', 'data': cached_response})}\n\n"
            yield "data: [DONE]\n\n"
            return
        
        # Step 2: Process query
        yield f"data: {json.dumps({'type': 'status', 'message': 'Analyzing query...', 'timestamp': time.time()})}\n\n"
        
        query_analysis = query_processor.preprocess_query(payload.question)
        
        # Step 3: Document retrieval
        yield f"data: {json.dumps({'type': 'status', 'message': 'Retrieving relevant documents...', 'timestamp': time.time()})}\n\n"
        
        if enhanced_retriever:
            filters = query_analysis.get('filters', {})
            # Use parallel async retrieval with reduced document count for speed
            relevant_docs = enhanced_retriever.retrieve_with_filters(
                query=payload.question,
                filters=filters,
                k=2  # Further reduced from 3 to 2 for faster processing
            )
        else:
            retriever = vectorstore.as_retriever(search_kwargs={"k": 2})  # Reduced from 3 to 2
            relevant_docs = retriever.get_relevant_documents(payload.question)
        
        # Step 4: Reranking and confidence
        yield f"data: {json.dumps({'type': 'status', 'message': 'Processing documents...', 'timestamp': time.time()})}\n\n"
        
        # Quick reranking
        enriched = []
        for doc in relevant_docs[:3]:
            meta = getattr(doc, "metadata", {}) or {}
            doc_id = meta.get("id") or meta.get("source_file") or meta.get("source") or f"{meta.get('source','unknown')}:{meta.get('page','-')}"
            
            try:
                similarity_score = float(getattr(doc, "score", None) or meta.get("similarity") or 0.0)
            except Exception:
                similarity_score = 0.0
            
            enriched.append((similarity_score, doc))
        
        enriched.sort(key=lambda x: x[0], reverse=True)
        relevant_docs = [doc for _, doc in enriched]
        
        confidence = calculate_confidence(relevant_docs, query_analysis)
        context = format_context(relevant_docs)
        
        # Step 5: Generate streaming response
        yield f"data: {json.dumps({'type': 'status', 'message': 'Generating response...', 'timestamp': time.time()})}\n\n"
        
        # Setup streaming callback
        streaming_handler = StreamingCallbackHandler()
        cost_callback = CostTrackingCallback(user_id=payload.user_id, request_id=request_id)
        
        # Model configuration for streaming
        max_tokens = 800 if payload.complexity_level in ['simple', 'beginner'] else 1200
        
        llm = ChatOpenAI(
            temperature=0,
            model="gpt-3.5-turbo",
            openai_api_key=settings.openai_api_key,
            callbacks=[streaming_handler, cost_callback],
            max_tokens=max_tokens,
            timeout=8,
            streaming=True  # Enable streaming
        )
        
        # Prepare prompt
        max_context_length = 6000
        if len(context) > max_context_length:
            context = context[:max_context_length] + "\n... [Context truncated for performance]"
        
        prompt = ENHANCED_LEGAL_PROMPT.format(
            complexity_level=payload.complexity_level,
            query_analysis=query_analysis,
            context=context
        )
        
        # Start streaming generation
        accumulated_response = ""
        
        # Use async streaming with immediate yielding
        try:
            async for chunk in llm.astream([
                {"role": "system", "content": prompt},
                {"role": "user", "content": payload.question}
            ]):
                if hasattr(chunk, 'content') and chunk.content:
                    content = chunk.content
                    accumulated_response += content
                    
                    # Yield each token/chunk immediately for real-time streaming
                    yield f"data: {json.dumps({'type': 'token', 'content': content, 'timestamp': time.time()})}\n\n"
                    
        except Exception as stream_error:
            logger.error(f"Streaming generation error: {stream_error}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Streaming failed, falling back to regular generation', 'timestamp': time.time()})}\n\n"
            
            # Fallback to regular generation if streaming fails
            response = await llm.ainvoke([
                {"role": "system", "content": prompt},
                {"role": "user", "content": payload.question}
            ])
            accumulated_response = response.content
            yield f"data: {json.dumps({'type': 'token', 'content': accumulated_response, 'timestamp': time.time()})}\n\n"
        
        # Generate final response data
        end_time = time.time()
        response_time = int((end_time - start_time) * 1000)
        
        citations = extract_citations(relevant_docs)
        formatted_sources = []
        seen_sources = set()
        
        for doc in relevant_docs:
            source_name = doc.metadata.get('source_file', 'Unknown')
            if source_name not in seen_sources:
                formatted_sources.append({
                    "source": source_name,
                    "page": doc.metadata.get('page', 'N/A'),
                    "document_type": doc.metadata.get('document_type', 'other'),
                    "relevance_snippet": doc.page_content[:200] + "..."
                })
                seen_sources.add(source_name)
        
        final_data = {
            "answer": accumulated_response,
            "source_documents": formatted_sources,
            "confidence": confidence,
            "tools_used": [],
            "citations": citations,
            "reading_level": payload.complexity_level,
            "response_time_ms": response_time,
            "query_analysis": query_analysis,
            "retrieval_stats": {
                "documents_retrieved": len(relevant_docs),
                "unique_sources": len(formatted_sources),
                "average_relevance": confidence
            },
            "from_cache": False
        }
        
        # Cache the response
        cache.set_cached_query(cache_key, final_data, expire=1800)
        
        # Record latency
        try:
            latency_tracker.record_latency("enhanced-chat", response_time, payload.user_id)
            
            metadata = {
                "complexity_level": payload.complexity_level,
                "from_cache": False,
                "tools_used": 0,
                "confidence": confidence,
                "documents_retrieved": len(relevant_docs),
                "source": "streaming_handler"
            }
            
            LatencyMetricService.record_latency(
                db=db,
                endpoint="enhanced-chat",
                latency_ms=response_time,
                user_id=payload.user_id,
                request_id=request_id,
                latency_metadata=metadata
            )
        except Exception as e:
            logger.warning(f"Failed to record streaming latency: {e}")
        
        # Send final completion
        yield f"data: {json.dumps({'type': 'complete', 'data': final_data})}\n\n"
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'timestamp': time.time()})}\n\n"
        yield "data: [DONE]\n\n"

async def execute_tools_parallel(tools_data: List[Dict], max_workers: int = 2, timeout: int = 15) -> List[Dict]:
    """
    Execute multiple tools in parallel with timeout and error handling.
    
    Args:
        tools_data: List of dicts with 'name', 'func', and 'kwargs' for each tool
        max_workers: Maximum concurrent tools to run
        timeout: Timeout in seconds for each tool
        
    Returns:
        List of tool results (success or error)
    """
    
    def run_single_tool(tool_info: Dict) -> Dict:
        """Run a single tool with timeout"""
        tool_name = tool_info.get('name', 'unknown')
        tool_func = tool_info.get('func')
        tool_kwargs = tool_info.get('kwargs', {})
        
        start_time = time.time()
        try:
            logger.info(f"Starting parallel tool execution: {tool_name}")
            result = tool_func(**tool_kwargs)
            elapsed = time.time() - start_time
            
            logger.info(f"Tool {tool_name} completed in {elapsed:.2f}s")
            return {
                'tool_name': tool_name,
                'success': True,
                'result': result,
                'execution_time_ms': int(elapsed * 1000)
            }
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Tool {tool_name} failed after {elapsed:.2f}s: {e}")
            return {
                'tool_name': tool_name,
                'success': False,
                'error': str(e),
                'execution_time_ms': int(elapsed * 1000)
            }
    
    async def run_with_timeout(tool_info: Dict) -> Dict:
        """Run tool with async timeout"""
        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = loop.run_in_executor(executor, run_single_tool, tool_info)
                return await asyncio.wait_for(future, timeout=timeout)
                
        except asyncio.TimeoutError:
            tool_name = tool_info.get('name', 'unknown')
            logger.error(f"Tool {tool_name} timed out after {timeout}s")
            return {
                'tool_name': tool_name,
                'success': False,
                'error': f'Tool execution timed out after {timeout} seconds',
                'execution_time_ms': timeout * 1000
            }
        except Exception as e:
            tool_name = tool_info.get('name', 'unknown')
            logger.error(f"Tool {tool_name} execution error: {e}")
            return {
                'tool_name': tool_name,
                'success': False,
                'error': str(e),
                'execution_time_ms': 0
            }
    
    # Limit concurrent execution
    semaphore = asyncio.Semaphore(max_workers)
    
    async def run_tool_with_semaphore(tool_info: Dict) -> Dict:
        async with semaphore:
            return await run_with_timeout(tool_info)
    
    # Execute all tools concurrently
    logger.info(f"Executing {len(tools_data)} tools in parallel (max_workers={max_workers})")
    start_time = time.time()
    
    tasks = [run_tool_with_semaphore(tool_info) for tool_info in tools_data]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    total_time = time.time() - start_time
    logger.info(f"Parallel tool execution completed in {total_time:.2f}s")
    
    # Handle any exceptions from gather
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            tool_name = tools_data[i].get('name', f'tool_{i}')
            processed_results.append({
                'tool_name': tool_name,
                'success': False,
                'error': str(result),
                'execution_time_ms': int(total_time * 1000)
            })
        else:
            processed_results.append(result)
    
    return processed_results

async def execute_tools_intelligently(
    query: str, 
    context: str, 
    complexity_level: str,
    llm: ChatOpenAI,
    confidence: float
) -> tuple[str, List[str]]:
    """
    Intelligently decide which tools to run and execute them in parallel
    """
    from tools.tool import fetch_legal_citations, summarize_legal_section, find_similar_cases
    
    # Analyze query to determine which tools are needed
    tools_to_run = []
    
    # Check if we need citations
    if any(keyword in query.lower() for keyword in ['section', 'act', 'law', 'provision', 'cite']):
        tools_to_run.append({
            'name': 'fetch_legal_citations',
            'func': fetch_legal_citations,
            'kwargs': {'legal_query': query, 'jurisdiction': 'India'}
        })
    
    # Check if we need section explanation
    section_pattern = r'(section|sec|article|art)\s+(\d+[a-z]*)'
    if re.search(section_pattern, query.lower()) or complexity_level in ['simple', 'beginner']:
        # Extract section reference if present
        match = re.search(section_pattern, query.lower())
        section_ref = match.group(2) if match else query.split()[:3]  # fallback
        
        tools_to_run.append({
            'name': 'summarize_legal_section', 
            'func': summarize_legal_section,
            'kwargs': {'section_reference': str(section_ref), 'complexity_level': complexity_level}
        })
    
    # Check if we need case precedents (only if confidence is very low)
    if confidence < 0.4 and any(keyword in query.lower() for keyword in ['case', 'precedent', 'judgment', 'ruling']):
        tools_to_run.append({
            'name': 'find_similar_cases',
            'func': find_similar_cases, 
            'kwargs': {'case_facts': query, 'case_type': 'any'}
        })
    
    if not tools_to_run:
        # No tools needed, use direct LLM
        return await generate_direct_response(query, context, complexity_level, llm), []
    
    # Execute tools in parallel
    print(f'⏱️ PARALLEL TOOL START: Running {len(tools_to_run)} tools')
    tool_start = time.time()
    
    tool_results = await execute_tools_parallel(tools_to_run, max_workers=2, timeout=12)
    
    tool_time = (time.time() - tool_start) * 1000
    print(f'⏱️ PARALLEL TOOL COMPLETE: {tool_time:.1f}ms')
    
    # Combine tool results with context
    enhanced_context = context + "\n\nTool Results:\n"
    tools_used = []
    
    for tool_result in tool_results:
        if tool_result.get('success'):
            result = tool_result.get('result', {})
            tool_name = tool_result.get('tool_name')
            tools_used.append(tool_name)
            
            if tool_name == 'fetch_legal_citations':
                citations = result.get('citations', [])
                enhanced_context += f"\nCitations found: {len(citations)} sources\n"
                for cite in citations[:3]:  # Limit to top 3
                    enhanced_context += f"- {cite.get('source')}, Page {cite.get('page')}\n"
                    
            elif tool_name == 'summarize_legal_section':
                summary = result.get('summary', '')
                enhanced_context += f"\nSection Summary: {summary[:300]}...\n"
                
            elif tool_name == 'find_similar_cases':
                cases = result.get('cases', [])
                enhanced_context += f"\nSimilar cases found: {len(cases)}\n"
                for case in cases[:2]:  # Limit to top 2
                    enhanced_context += f"- {case.get('source')}: {case.get('excerpt', '')[:100]}...\n"
        else:
            logger.warning(f"Tool {tool_result.get('tool_name')} failed: {tool_result.get('error')}")
    
    # Generate final response with enhanced context
    final_response = await generate_direct_response(query, enhanced_context, complexity_level, llm)
    return final_response, tools_used

async def generate_direct_response(query: str, context: str, complexity_level: str, llm: ChatOpenAI) -> str:
    """Generate response using direct LLM call"""
    prompt = ENHANCED_LEGAL_PROMPT.format(
        complexity_level=complexity_level,
        query_analysis={},  # Not needed for direct response
        context=context
    )
    
    response = llm.invoke([
        {"role": "system", "content": prompt},
        {"role": "user", "content": query}
    ])
    
    return response.content

@router.post("/enhanced-chat-stream")
async def enhanced_chat_stream(
    payload: EnhancedChatRequest,
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Streaming version of enhanced chat endpoint using Server-Sent Events (SSE)
    """
    try:   
        request_id = None
        try:
            request_id = payload.request_id or http_request.headers.get("x-request-id")
        except Exception:
            pass

        return StreamingResponse(
            stream_response_generator(payload, db, request_id),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except Exception as e:
        logger.error(f"Streaming endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "STREAMING_ERROR",
                "error_message": "Failed to start streaming response"
            }
        )

@router.post("/enhanced-chat", response_model=EnhancedChatResponse)
async def enhanced_chat(
    payload: EnhancedChatRequest,
    db: Session = Depends(get_db),
    http_request: Request = None):
    start_time = time.time()
    print(f'🚀 REQUEST START: {start_time}')

    try:
        request_id = None
        try:
            request_id = payload.request_id or http_request.headers.get("x-request-id")
        except Exception:
            pass

        # Step 1: Check cache first
        cache_start = time.time()
        cache_key = f"{payload.question}_{payload.complexity_level}"
        cached_response = cache.get_cached_query(cache_key)
        print(f'⏱️  CACHE CHECK: {(time.time() - cache_start)*1000:.1f}ms')

        if cached_response:
            logger.info(f"Cache hit for query: {payload.question}")
            cached_response["response_time_ms"] = int((time.time() - start_time) * 1000)
            cached_response["from_cache"] = True
            
            # Record latency for cached responses in both memory and database
            try:
                cache_latency = cached_response["response_time_ms"]
                
                # Record in memory (Redis) for real-time metrics
                latency_tracker.record_latency("enhanced-chat-cache", cache_latency, payload.user_id)
                
                # Also record in database for persistent analytics
                cache_metadata = {
                    "complexity_level": payload.complexity_level,
                    "from_cache": True,
                    "tools_used": 0,
                    "confidence": "N/A",
                    "documents_retrieved": 0,
                    "source": "cache_hit"
                }
                
                LatencyMetricService.record_latency(
                    db=db,
                    endpoint="enhanced-chat",
                    latency_ms=cache_latency,
                    user_id=payload.user_id,
                    request_id=request_id,
                    latency_metadata=cache_metadata
                )
                
                logger.info(f"Recorded cache hit latency: {cache_latency}ms for enhanced-chat")
                
            except Exception as e:
                logger.warning(f"Failed to record cache latency metrics: {e}")
            
            return EnhancedChatResponse(**cached_response)

        # Step 2: Process and analyze query
        query_start = time.time()
        query_analysis = query_processor.preprocess_query(payload.question)
        print(f'⏱️  QUERY ANALYSIS: {(time.time() - query_start)*1000:.1f}ms')

        # Step 4: Enhanced retrieval
        retrieval_start = time.time()
        if enhanced_retriever:
            # Use hybrid retriever with filters - further reduced documents for speed
            filters = query_analysis.get('filters', {})
            relevant_docs = enhanced_retriever.retrieve_with_filters(
                query=payload.question,
                filters=filters,
                k=2  # Further reduced from 3 to 2 for faster processing
        )
        else:
            # Fallback to basic retrieval - also reduced
            retriever = vectorstore.as_retriever(search_kwargs={"k": 2})  # Reduced from 3 to 2
            relevant_docs = retriever.get_relevant_documents(payload.question)
        print(f'⏱️  DOCUMENT RETRIEVAL: {(time.time() - retrieval_start)*1000:.1f}ms')

        # Reranking step - optimized for speed
        rerank_start = time.time()
        enriched = []
        for doc in relevant_docs[:2]:  # Only rerank top 2 for speed
            meta = getattr(doc, "metadata", {}) or {}
            doc_id = meta.get("id") or meta.get("source_file") or meta.get("source") or f"{meta.get('source','unknown')}:{meta.get('page','-')}"

            try:
                similiarity_score = float(getattr(doc, "score", None) or meta.get("similarity") or 0.0)
            except Exception:
                similiarity_score = 0.0
            
            eval_score = 0
            try:
                raw = cache.get(f"eval_score:{doc_id}")
                if raw:
                    parsed = raw if isinstance(raw, dict) else json.loads(raw)
                    eval_score = float(parsed.get("score", 0.0))
            except Exception:
                logger.debug("Could not load eval_score for %s", doc_id)  # Reduced to debug level

            combined = (EVAL_ALPHA * similiarity_score) + (EVAL_BETA * eval_score)
            enriched.append((combined, doc))

        enriched.sort(key=lambda x: x[0], reverse=True)

        # replace relevant_docs with reranked docs
        relevant_docs = [doc for _, doc in enriched]
        logger.debug(f"Reranked {len(relevant_docs)} documents")  # Reduced logging
        print(f'⏱️  RERANKING: {(time.time() - rerank_start)*1000:.1f}ms')

        # Step 5: Calculate confidence based on retrieval quality
        confidence_start = time.time()
        confidence = calculate_confidence(relevant_docs, query_analysis)
        print(f'⏱️  CONFIDENCE CALC: {(time.time() - confidence_start)*1000:.1f}ms')

        # Step 6: Prepare context for LLM
        context_start = time.time()
        context = format_context(relevant_docs)
        print(f'⏱️  CONTEXT FORMATTING: {(time.time() - context_start)*1000:.1f}ms')

        cost_callback = CostTrackingCallback(user_id=payload.user_id, request_id=request_id)

        # Step 7: Use LLM to generate answer - model selection for speed
        llm_start = time.time()
        
        # Use faster model for simple queries
        model_name = "gpt-3.5-turbo"
        max_tokens = 1200
        
        # For simple/beginner complexity, use even faster settings
        if payload.complexity_level in ['simple', 'beginner']:
            max_tokens = 800  # Shorter responses for simple queries
        
        llm = ChatOpenAI(
            temperature=0, 
            model=model_name,
            openai_api_key=settings.openai_api_key,
            callbacks=[cost_callback],
            max_tokens=max_tokens,
            timeout=8,
            )
        print(f'⏱️  LLM INIT: {(time.time() - llm_start)*1000:.1f}ms')

        generation_start = time.time()
        if confidence < 0.3:  # Reduced threshold - only use tools for very low confidence
            answer, tools_used = await execute_tools_intelligently(
                query=payload.question,
                context=context,
                complexity_level=payload.complexity_level,
                llm=llm,
                confidence=confidence
            )
        else:
            # Use direct LLM with context - optimized for speed
            # Truncate context if too long to speed up processing
            max_context_length = 6000  # Reduced from 8000 for faster processing
            if len(context) > max_context_length:
                context = context[:max_context_length] + "\n... [Context truncated for performance]"
                
            prompt = ENHANCED_LEGAL_PROMPT.format(
                complexity_level=payload.complexity_level,
                query_analysis=query_analysis,
                context=context
            )
            
            # Add streaming for faster perceived response (if needed)
            response = llm.invoke([
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": payload.question
                }
            ])
            answer = response.content
            tools_used = []
        print(f'⏱️  LLM GENERATION: {(time.time() - generation_start)*1000:.1f}ms')
        
        # Extract citations from documents
        citation_start = time.time()
        citations = extract_citations(relevant_docs)
        print(f'⏱️  CITATIONS: {(time.time() - citation_start)*1000:.1f}ms')
        
        # Format source documents (avoid duplicates)
        formatting_start = time.time()
        formatted_sources = []
        seen_sources = set()
        
        for doc in relevant_docs:
            source_name = doc.metadata.get('source_file', 'Unknown')
            if source_name not in seen_sources:
                extracted_sections = doc.metadata.get('extracted_sections', [])
                legal_topics = doc.metadata.get('legal_topics', [])

                if isinstance(extracted_sections, str):
                    extracted_sections = [] if extracted_sections.strip() == '' else [extracted_sections]
                if isinstance(legal_topics, str):
                    legal_topics = [] if legal_topics.strip() == '' else [legal_topics]
                
                formatted_sources.append({
                    "source": source_name,
                    "page": doc.metadata.get('page', 'N/A'),
                    "document_type": doc.metadata.get('document_type', 'other'),
                    "relevance_snippet": doc.page_content[:200] + "...",
                    "sections": extracted_sections,
                    "legal_topics": legal_topics
                })
                seen_sources.add(source_name)
        print(f'⏱️  SOURCE FORMATTING: {(time.time() - formatting_start)*1000:.1f}ms')

        # Step 8: Format response
        response_building_start = time.time()
        end_time = time.time()
        response_time = int((end_time - start_time) * 1000)
        
        print(f'🚀 REQUEST START: {start_time}')
        print(f'🏁 REQUEST END: {end_time}')
        print(f'⏱️  TOTAL DURATION: {end_time - start_time:.3f} seconds')
        print(f'⏱️  TOTAL RESPONSE TIME: {response_time} ms')

        response_data = {
            "answer": answer,
            "source_documents": formatted_sources,
            "confidence": confidence,
            "tools_used": tools_used,
            "citations": citations,
            "reading_level": payload.complexity_level,
            "response_time_ms": response_time,
            "query_analysis": query_analysis,
            "retrieval_stats": {
                "documents_retrieved": len(relevant_docs),
                "unique_sources": len(set(doc.metadata.get('source_file') for doc in relevant_docs)),
                "average_relevance": confidence
            },
            "from_cache": False
        }
        print(f'⏱️  RESPONSE BUILDING: {(time.time() - response_building_start)*1000:.1f}ms')

        # cache the response for future use
        cache_save_start = time.time()
        cache.set_cached_query(cache_key, response_data, expire=1800)
        print(f'⏱️  CACHE SAVE: {(time.time() - cache_save_start)*1000:.1f}ms')
        
        # Record latency metrics (middleware handles this too, but we add metadata here)
        latency_recording_start = time.time()
        try:
            # Record in-memory with enhanced metadata
            latency_tracker.record_latency("enhanced-chat", response_time, payload.user_id)
            
            # Also store in database with additional metadata
            metadata = {
                "complexity_level": payload.complexity_level,
                "from_cache": False,
                "tools_used": len(tools_used),
                "confidence": confidence,
                "documents_retrieved": len(relevant_docs),
                "source": "route_handler"  # Distinguish from middleware
            }
            
            LatencyMetricService.record_latency(
                db=db,
                endpoint="enhanced-chat",
                latency_ms=response_time,
                user_id=payload.user_id,
                request_id=request_id,
                latency_metadata=metadata
            )
            
            logger.info(f"Recorded latency: {response_time}ms for enhanced-chat")
            
        except Exception as e:
            logger.warning(f"Failed to record latency metrics: {e}")
        print(f'⏱️  LATENCY RECORDING: {(time.time() - latency_recording_start)*1000:.1f}ms')
        
        final_end = time.time()
        print(f'🏁 FINAL END: {final_end}')
        print(f'⏱️  FINAL TOTAL: {(final_end - start_time)*1000:.1f}ms')
        
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
    
async def validation_exception_handler(payload: Request, exc):
    """Handle validation errors with structured response."""
    logger.warning(f"Validation error on {payload.url.path}: {exc}")
    
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
    """Extract structured citations from documents with robust metadata handling"""
    
    def _ensure_list(value):
        """Ensure a value is a list, handling ChromaDB serialization issues"""
        if isinstance(value, list):
            return value
        elif isinstance(value, str):
            # Convert empty strings to empty lists (ChromaDB serialization issue)
            return [] if value.strip() == '' else [value]
        elif value is None:
            return []
        else:
            return [str(value)]
    
    citations = []
    seen = set()
    
    for doc in docs:
        source = doc.metadata.get('source_file', 'Unknown')
        if source not in seen:
            citation = {
                "source": source,
                "type": doc.metadata.get('document_type', 'legal_document'),
                "sections": _ensure_list(doc.metadata.get('extracted_sections', [])),
                "acts": _ensure_list(doc.metadata.get('extracted_acts', [])),
                "page": doc.metadata.get('page', 'N/A')
            }
            citations.append(citation)
            seen.add(source)
    
    return citations