from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
from langchain_openai import ChatOpenAI
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Optional, List, Dict, Any

from chain.loader import vectorstore
from tools.tool import ALL_TOOLS
from services.cost_tracking_callback_service import CostTrackingCallback

router = APIRouter()

class ChatRequest(BaseModel):
    question: str
    user_id: str 
    session_id: str = "default"
    use_tools: bool = True
    complexity_level: str = "simple"  # simple, intermediate, advanced

class ChatResponse(BaseModel):
    answer: str
    source_documents: list[str]
    confidence: float
    tools_used: Optional[List[str]] = None
    citations: Optional[List[Dict]] = None
    reading_level: str = "simple"

LEGAL_ASSISTANT_PROMPT = """You are an expert AI Legal Assistant specializing in Indian law. Your role is to:

1. Provide accurate, well-cited answers to legal questions
2. Use available tools to fetch citations, explain sections, and find similar cases
3. Adjust your explanation complexity based on user preference
4. Always include proper citations and sources
5. Clearly state when you're uncertain or when a human lawyer should be consulted

Available tools:
- fetch_legal_citations: Get relevant legal citations and references
- summarize_legal_section: Explain specific legal sections in simple terms
- find_similar_cases: Find precedent cases based on facts

Guidelines:
- Always cite your sources
- For complex legal matters, recommend consulting a qualified lawyer
- Explain legal concepts clearly based on the requested complexity level
- Use tools proactively to provide comprehensive answers
- If you cannot find relevant information, say so clearly

Current complexity level: {complexity_level}
"""

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        llm = ChatOpenAI(temperature=0, model="gpt-4o-mini")

        if request.use_tools:
            print("Using tools for the request")
            prompt = ChatPromptTemplate.from_messages([
                ("system", LEGAL_ASSISTANT_PROMPT.format(complexity_level=request.complexity_level)),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}")
            ])
            agent = create_openai_tools_agent(
                llm=llm,
                tools=ALL_TOOLS,
                prompt=prompt,
            )
            # Create callback
            cost_callback = CostTrackingCallback(user_id=request.user_id)
            
            agent_executor = AgentExecutor(
                agent=agent,
                tools=ALL_TOOLS,
                verbose=True,
                callbacks=[cost_callback]
            )
            result = agent_executor.invoke({
                "input": request.question,
            })

            return ChatResponse(
                answer=result['output'],
                source_documents=["Tool-enhancd response"],
                confidence=0.95,
                tools_used=[tool.name for tool in ALL_TOOLS],
                reading_level=request.complexity_level
            )
        else:
            print("Using retrieval QA for the request")
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
                return_source_documents=True
            )
            result = qa_chain.invoke({"query": request.question})

            sources = [doc.metadata.get('source_file', 'Unknown') 
                    for doc in result['source_documents']]
            
            return ChatResponse(
                answer=result['result'],
                source_documents=sources,
                confidence=0.95,  # Placeholder confidence value
                reading_level=request.complexity_level
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/tools/citations")
async def get_citations_only(query: str):
    """Endpoint to get just citations for a query"""
    try:
        from tools.tool import fetch_legal_citations
        result = fetch_legal_citations.invoke({"legal_query": query})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/tools/explain-section")
async def explain_section(section: str, complexity: str = "simple"):
    """Endpoint to explain a specific legal section"""
    try:
        from tools.tool import summarize_legal_section
        result = summarize_legal_section.invoke({
            "section_reference": section,
            "complexity_level": complexity
        })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))