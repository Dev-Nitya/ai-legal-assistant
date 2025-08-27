"""
Error response models for consistent error handling.

Contains only error response schemas, no error handling logic.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from .base import BaseResponseModel

class ErrorResponseModel(BaseResponseModel):
    """Base error response model."""
    
    success: bool = Field(False)
    error_code: str = Field(..., description="Machine-readable error code")
    error_message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error_code": "VALIDATION_ERROR",
                "error_message": "Invalid input provided",
                "details": {
                    "field": "question",
                    "reason": "Question too short"
                },
                "timestamp": "2024-01-15T10:30:00Z",
                "request_id": "req_123"
            }
        }

class ValidationErrorResponse(ErrorResponseModel):
    """Validation error response model."""
    
    error_code: str = Field("VALIDATION_ERROR", const=True)
    field_errors: Optional[Dict[str, List[str]]] = Field(
        None, 
        description="Field-specific validation errors"
    )

class RateLimitErrorResponse(ErrorResponseModel):
    """Rate limit error response model."""
    
    error_code: str = Field("RATE_LIMIT_EXCEEDED", const=True)
    retry_after_seconds: int = Field(..., description="Seconds to wait before retry")
    current_usage: Dict[str, int] = Field(..., description="Current usage statistics")

class SecurityErrorResponse(ErrorResponseModel):
    """Security violation error response."""
    
    error_code: str = Field("SECURITY_VIOLATION", const=True)
    violation_type: str = Field(..., description="Type of security violation detected")

class ContentPolicyErrorResponse(ErrorResponseModel):
    """Content policy violation error response."""
    
    error_code: str = Field("CONTENT_POLICY_VIOLATION", const=True)
    policy_violations: List[str] = Field(..., description="List of policy violations")

class InternalErrorResponse(ErrorResponseModel):
    """Internal server error response."""
    
    error_code: str = Field("INTERNAL_ERROR", const=True)
    incident_id: Optional[str] = Field(None, description="Incident tracking ID")