"""
Chat-specific Pydantic models for request/response validation.

Contains only schema definitions, no validation logic.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime

from schemas.base import BaseRequestModel, BaseResponseModel, ComplexityLevel, DocumentType
from schemas.validation import ValidationError
from validators.legal import validate_legal_question
from validators.security import detect_prompt_injection

import logging
logger = logging.getLogger(__name__)

class ChatRequest(BaseRequestModel):
    """Basic chat request model."""

    question: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Legal question to ask the AI assistant",
        example="What are the key elements of a valid contract under common law?"
    )

    complexity_level: ComplexityLevel = Field(
        ComplexityLevel.SIMPLE,
        description="Desired complexity level for the response"
    )

    @field_validator('question')
    def validate_question_content(cls, v):
        try:
            validated = validate_legal_question(v)

            # Check for prompt injection
            is_suspicious, patterns = detect_prompt_injection(validated)
            if is_suspicious:
                raise ValidationError(f"Potentially harmful content detected: {patterns[0]}")
            return validated
        except ValidationError as e:
            raise ValueError(str(e))
        
    class Config:
        schema_extra = {
            "example": {
                "question": "What are the statutory requirements for forming a valid LLC in Delaware?",
                "complexity_level": "intermediate",
                "request_id": "req_001"
            }
        }

class EnhancedChatRequest(BaseRequestModel):
    """Enhanced chat request with advanced filtering and options."""
    
    user_id: str

    question: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Legal question to ask the AI assistant"
    )
    
    complexity_level: ComplexityLevel = Field(
        ComplexityLevel.SIMPLE,
        description="Desired complexity level for the response"
    )
    
    max_sources: int = Field(
        5,
        ge=1,
        le=10,
        description="Maximum number of source documents to retrieve"
    )

    @field_validator('question')
    def validate_question_content(cls, v):
        try:
            validated = validate_legal_question(v)
            is_suspicious, patterns = detect_prompt_injection(validated)
            if is_suspicious:
                raise ValidationError(f"Potentially harmful content detected: {patterns[0]}")
            return validated
        except ValidationError as e:
            raise ValueError(str(e))
    
    
    class Config:
        schema_extra = {
            "example": {
                "question": "What are the liability implications for directors in a Delaware C-Corp during bankruptcy proceedings?",
                "complexity_level": "advanced",
                "max_sources": 5,
                "request_id": "req_enhanced_001"
            }
        }

class SourceDocument(BaseModel):
    """Model for source document information in responses."""
    
    source: str = Field(..., description="Source file or document name")
    page: Union[int, str] = Field(..., description="Page number or section")
    document_type: DocumentType = Field(..., description="Type of legal document")
    relevance_snippet: str = Field(
        ..., 
        max_length=500,
        description="Relevant excerpt from the document"
    )
    sections: List[str] = Field(
        default_factory=list,
        description="Document sections that are relevant"
    )
    legal_topics: List[str] = Field(
        default_factory=list,
        description="Legal topics covered in this source"
    )
    confidence_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Relevance confidence score"
    )

class QueryAnalysis(BaseModel):
    """Model for query analysis information."""
    
    legal_domain: Optional[str] = Field(None, description="Identified legal domain")
    intent: Optional[str] = Field(None, description="Query intent classification")
    entities: List[str] = Field(default_factory=list, description="Legal entities mentioned")
    complexity_detected: Optional[ComplexityLevel] = Field(None, description="Detected complexity level")
    suggested_filters: Optional[Dict[str, Any]] = Field(None, description="Suggested search filters")

class RetrievalStats(BaseModel):
    """Model for retrieval statistics."""
    
    documents_retrieved: int = Field(ge=0, description="Number of documents retrieved")
    unique_sources: int = Field(ge=0, description="Number of unique source documents")
    average_relevance: float = Field(ge=0.0, le=1.0, description="Average relevance score")
    search_time_ms: Optional[int] = Field(None, ge=0, description="Search time in milliseconds")

class ChatResponse(BaseResponseModel):
    """Standard chat response model."""
    
    answer: str = Field(..., description="AI assistant's response")
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence in the response accuracy"
    )
    sources: List[SourceDocument] = Field(
        default_factory=list,
        description="Source documents used for the response"
    )
    response_time_ms: int = Field(ge=0, description="Response time in milliseconds")

class EnhancedChatResponse(BaseResponseModel):
    """Enhanced chat response with comprehensive information."""
    
    answer: str = Field(..., description="AI assistant's response")
    confidence: float = Field(ge=0.0, le=1.0, description="Response confidence")
    source_documents: List[SourceDocument] = Field(
        default_factory=list,
        description="Source documents with full metadata"
    )
    tools_used: List[str] = Field(
        default_factory=list,
        description="Legal tools used in generating the response"
    )
    citations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Formatted citations for legal sources"
    )
    reading_level: ComplexityLevel = Field(description="Actual complexity level of response")
    response_time_ms: int = Field(ge=0, description="Total response time")
    query_analysis: Optional[QueryAnalysis] = Field(None, description="Analysis of the user query")
    retrieval_stats: Optional[RetrievalStats] = Field(None, description="Document retrieval statistics")
    from_cache: bool = Field(False, description="Whether response was served from cache")
    cost_estimate: Optional[Dict[str, float]] = Field(
        None, 
        description="Estimated costs for this request"
    )