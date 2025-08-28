"""
Base models and common types for all schemas.

Contains foundational Pydantic models and enums used across the application.
"""

from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class ComplexityLevel(str, Enum):
    """
    Base models and common types for all schemas.

    Contains foundational Pydantic models and enums used across the application.
    """
    SIMPLE = "simple"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class DocumentType(str, Enum):
    """
    Supported legal document types for filtering and categorization.
    
    Used to ensure consistent document classification across the system.
    """
    CONTRACT = "contract"
    CASE_LAW = "case_law"
    STATUTE = "statute"
    REGULATION = "regulation"
    LEGAL_BRIEF = "legal_brief"
    COURT_FILING = "court_filing"
    LEGAL_MEMO = "legal_memo"
    OTHER = "other"

class BaseRequestModel(BaseModel):
    """
    Base model for all API requests.
    
    Provides common fields and configuration for request validation.
    All request models should inherit from this.
    """
    request_id: Optional[str] = Field(
        None,
        description="Optional request tracking ID for debugging and correlation",
        pattern=r"^[a-zA-Z0-9\-_]{1,50}$"
    )

    class Config:
        # Pydantic configuration for all request models
        str_strip_whitespace = True  # Auto-trim whitespace from strings
        validate_assignment = True   # Validate when fields are assigned
        use_enum_values = True      # Use enum values in JSON serialization
        extra = "forbid"            # Reject unknown fields in requests

class BaseResponseModel(BaseModel):
    """
    Base model for all API responses.
    
    Ensures consistent response structure across all endpoints.
    All response models should inherit from this.
    """
    success: bool = Field(
        True,
        description="Indicates if the request was processed successfully"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the response was generated"
    )
    request_id: Optional[str] = Field(
        None, 
        description="Request tracking ID if provided in request"
    )

    class Config:
        use_enum_values = True  # Serialize enums as values, not names

class PaginationModel(BaseModel):
    """
    Standard pagination model for list endpoints.
    
    Provides consistent pagination across all endpoints that return lists.
    """
    page: int = Field(
        1, 
        ge=1, 
        le=1000, 
        description="Page number (1-based indexing)"
    )
    size: int = Field(
        10, 
        ge=1, 
        le=100, 
        description="Number of items per page"
    )
    
    @property
    def offset(self) -> int:
        """Calculate offset for database/search queries."""
        return (self.page - 1) * self.size