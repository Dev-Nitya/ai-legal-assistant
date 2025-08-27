"""
Pure validation functions for request data.

Contains only validation logic, no Pydantic models.
All functions are pure (no side effects) and testable in isolation.
"""

import re
from typing import Any, Dict, List

class ValidationError(Exception):
    """Custom validation error for domain-specific validation failures."""
    pass

def validate_text_length(text: str, min_length: int, max_length: int, field_name: str) -> str:
    """
    Validate text length and normalize whitespace.
    
    Args:
        text: Text to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length
        field_name: Name of field being validated (for error messages)
    
    Returns:
        Cleaned and validated text
        
    Raises:
        ValidationError: If text doesn't meet length requirements
    """
    if not text or not text.strip():
        raise ValidationError(f"{field_name} cannot be empty or whitespace.")
    
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', text.strip())

    if len(cleaned) < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} characters long"
        )
    
    if len(cleaned) > max_length:
        raise ValidationError(
            f"{field_name} must be less than {max_length} characters"
        )
    
    return cleaned

def validate_no_excessive_repetition(text: str, max_consecutive: int = 10) -> None:
    """
    Check for excessive character repetition (spam detection).
    
    Args:
        text: Text to check
        max_consecutive: Maximum allowed consecutive identical characters
        
    Raises:
        ValidationError: If excessive repetition found
    """
    pattern = f'(.)\\1{{{max_consecutive},}}'
    if re.search(pattern, text):
        raise ValidationError("Text contains excessive repeated characters")
    
def validate_date_format(date_string: str, field_name: str) -> None:
    """
    Validate date string format (YYYY-MM-DD).
    
    Args:
        date_string: Date string to validate
        field_name: Field name for error messages
        
    Raises:
        ValidationError: If date format is invalid
    """
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_string):
        raise ValidationError(f"{field_name} must be in YYYY-MM-DD format")
    
def validate_document_types(doc_types: List[str]) -> List[str]:
    """
    Validate and normalize document type list.
    
    Args:
        doc_types: List of document type strings
        
    Returns:
        List of validated document types
        
    Raises:
        ValidationError: If any document type is invalid
    """ 
    from schemas.base import DocumentType

    valid_types = []
    for doc_type in doc_types:
        try:
            validated_type = DocumentType(doc_type.lower())
            valid_types.append(validated_type.value)
        except ValueError:
            valid_values = [dt.value for dt in DocumentType]
            raise ValidationError(
                f"Invalid document type: {doc_type}. "
                f"Valid types: {', '.join(valid_values)}"
            )
    return valid_types

def validate_legal_topics(topics: List[str]) -> List[str]:
    """
    Validate legal topics list.
    
    Args:
        topics: List of legal topic strings
        
    Returns:
        List of validated topics
        
    Raises:
        ValidationError: If any topic is invalid
    """
    validated_topics = []
    for topic in topics:
        topic = topic.strip()
        if len(topic) < 2:
            raise ValidationError("Legal topics must be at least 2 characters")
        if len(topic) > 50:
            raise ValidationError("Legal topics must be less than 50 characters")
        validated_topics.append(topic)
    
    return validated_topics

def validate_jurisdiction(jurisdiction: str) -> str:
    """
    Validate jurisdiction string.
    
    Args:
        jurisdiction: Jurisdiction string to validate
        
    Returns:
        Validated jurisdiction
        
    Raises:
        ValidationError: If jurisdiction is invalid
    """
    jurisdiction = jurisdiction.strip()
    if len(jurisdiction) < 2:
        raise ValidationError("Jurisdiction must be at least 2 characters")
    if len(jurisdiction) > 100:
        raise ValidationError("Jurisdiction must be less than 100 characters")
    return jurisdiction

def validate_filters_dict(filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate document filters dictionary.
    
    Args:
        filters: Dictionary of filter parameters
        
    Returns:
        Validated filters dictionary
        
    Raises:
        ValidationError: If any filter is invalid
    """
    if not filters:
        return {}
    
    validated_filters = {}

    # Validate document types
    if "document_types" in filters:
        doc_types = filters["document_types"]
        if isinstance(doc_types, str):
            doc_types = [doc_types]
        validated_filters["document_types"] = validate_document_types(doc_types)
    
    # Validate date range
    if "date_range" in filters:
        date_range = filters["date_range"]
        if not isinstance(date_range, dict):
            raise ValidationError("date_range must be an object")
        
    validated_date_range = {}
    if "start_date" in date_range:
        validate_date_format(date_range["start_date"], "start_date")
        validated_date_range["start_date"] = date_range["start_date"]
        
    if "end_date" in date_range:
        validate_date_format(date_range["end_date"], "end_date")
        validated_date_range["end_date"] = date_range["end_date"]
        
    validated_filters["date_range"] = validated_date_range

    # Validate jurisdiction
    if "jurisdiction" in filters:
        validated_filters["jurisdiction"] = validate_jurisdiction(
            filters["jurisdiction"]
        )
    
    # Validate legal topics
    if "legal_topics" in filters:
        topics = filters["legal_topics"]
        if isinstance(topics, str):
            topics = [topics]
        validated_filters["legal_topics"] = validate_legal_topics(topics)
    
    return validated_filters