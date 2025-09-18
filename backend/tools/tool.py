import re
import time
import asyncio
from functools import wraps
from langchain.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

from chain.loader import vectorstore
from config.settings import settings
from redis_cache.redis_cache import cache
import logging

logger = logging.getLogger(__name__)

def tool_timeout(seconds=10):
    """Decorator to add timeout to tool functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                if elapsed > seconds:
                    logger.warning(f"Tool {func.__name__} took {elapsed:.2f}s (timeout: {seconds}s)")
                return result
            except Exception as e:
                logger.error(f"Tool {func.__name__} error: {e}")
                return {"error": str(e)}
        return wrapper
    return decorator

def tool_cache(expire_seconds=300):
    """Decorator to cache tool results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"tool_cache:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache first
            try:
                cached_result = cache.get(cache_key)
                if cached_result:
                    logger.info(f"Tool cache hit for {func.__name__}")
                    return cached_result
            except Exception:
                pass
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            try:
                cache.set(cache_key, result, expire=expire_seconds)
                logger.info(f"Cached tool result for {func.__name__}")
            except Exception as e:
                logger.warning(f"Failed to cache tool result: {e}")
            
            return result
        return wrapper
    return decorator

class CitationRequest(BaseModel):
    """Input for citation request."""
    legal_query: str = Field(description="Legal question or topic to find citations for")
    jurisdiction: str = Field(default="India", description="Legal jurisdiction")

class SectionSummaryRequest(BaseModel):
    """Input for section summarizer"""
    section_reference: str = Field(description="Legal section reference (e.g., 'IPC 302', 'CrPC 154')")
    complexity_level: str = Field(default="simple", description="Explanation complexity: simple, intermediate, advanced")

class SimilarCaseRequest(BaseModel):
    """Input for similar case finder"""
    case_facts: str = Field(description="Brief description of case facts or legal issue")
    case_type: str = Field(default="any", description="Type of case: criminal, civil, constitutional, etc.")

@tool_timeout(10)
@tool_cache(600) 
@tool(args_schema=CitationRequest)
def fetch_legal_citations(legal_query: str, jurisdiction: str = "India") -> Dict:
    """
    Fetch relevant legal citations and references for a given legal query.
    Returns specific sections, acts, and case references.
    """
    try:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        docs = retriever.get_relevant_documents(legal_query)

        citations = []
        seen_sources = set()

        for doc in docs[:3]:
            source = doc.metadata.get("source_file", "Unknown")
            if source not in seen_sources:
                page = doc.metadata.get("page", "N/A")

                # Extract potential section references from content
                content = doc.page_content[:200]
                section_matches = re.findall(r'Section\s+(\d+[A-Z]*)', content)

                citation = {
                    "source": source,
                    "page": page,
                    "sections": section_matches,
                    "relevance_snippet": content,
                    "document_type": doc.metadata.get('document_type', 'legal_document')
                }

                citations.append(citation)
                seen_sources.add(source)

        return {
            "query": legal_query,
            "jurisdiction": jurisdiction,
            "citations_found": len(citations),
            "citations": citations[:5]
        }
    except Exception as e:
        return {"error": f"Failed to fetch citations: {str(e)}"}
    
@tool_timeout(15)  # 15 second timeout  
@tool_cache(1800)  # Cache for 30 minutes
@tool(args_schema=SectionSummaryRequest)
def summarize_legal_section(section_reference: str, complexity_level: str = "simple") -> Dict:
    """
    Provide a simplified explanation of a specific legal section.
    Adjusts complexity based on user preference.
    """
    try:
        llm = ChatOpenAI(
            temperature=0,
            model="gpt-3.5-turbo",
            openai_api_key=settings.openai_api_key,
            max_tokens=500,  # Limit response length
            timeout=10  # 10 second timeout for API call
        )
        
        search_query = f"Section {section_reference}"
        retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
        docs = retriever.get_relevant_documents(search_query)

        if not docs:
            return {
                "section": section_reference,
                "error": "Section not found in available documents"
            }
        
        primary_doc = docs[0]
        section_text = primary_doc.page_content

        prompt = f"""Explain this legal section in {complexity_level} terms (max 200 words):
        
        Section: {section_reference}
        Content: {primary_doc.page_content[:1000]}

        Provide a brief, clear explanation."""

        response = llm.invoke([{"role": "user", "content": prompt}])

        result = {
            'section': section_reference,
            'complexity_level': complexity_level,
            'summary': response.content,
            'source': primary_doc.metadata.get('source_file', 'Unknown'),
            'page': primary_doc.metadata.get('page', 'N/A'),
        }
        return result
    except Exception as e:
        return {"error": f"Failed to summarize section: {str(e)}"}
    
@tool(args_schema=SimilarCaseRequest)
def find_similar_cases(case_facts: str, case_type: str = "any") -> Dict:
    """
    Find similar legal cases based on provided facts.
    Returns brief summaries and references to similar cases.
    """
    try:
        if case_type.lower() != "any":
            search_query = f"{case_facts} {case_type} case law precedent"
        else:
            search_query = f"{case_facts} case law precedent judgment"

        retriever = vectorstore.as_retriever(search_kwargs={"k": 8})
        docs = retriever.get_relevant_documents(search_query)

        similar_cases = []
        for doc in docs:
            content = doc.page_content.lower()
            if any(keyword in content for keyword in ["judgment", "court", "petitioner", "respondent", "appellant"]):
                case_info = {
                    "source": doc.metadata.get('source_file', 'Unknown'),
                    "page": doc.metadata.get('page', 'N/A'),
                    "excerpt": doc.page_content[:300],
                    "relevance_score": 0.8  # Placeholder
                }
                similar_cases.append(case_info)

        return {
            "query_facts": case_facts,
            "case_type": case_type,
            "similar_cases_found": len(similar_cases),
            "cases": similar_cases[:4]  # Top 4 most relevant
        }
    except Exception as e:
        return {"error": f"Failed to find similar cases: {str(e)}"}
    
ALL_TOOLS = [
    fetch_legal_citations,
    summarize_legal_section,
    find_similar_cases
]