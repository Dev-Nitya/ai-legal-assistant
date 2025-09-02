"""
Pure validation functions for request data.

Contains only validation logic, no Pydantic models.
All functions are pure (no side effects) and testable in isolation.
"""

import re
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