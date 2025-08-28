"""
Security-focused validators for input sanitization and threat detection.
"""

import re
from typing import List, Optional, Tuple
from schemas.validation import ValidationError

def detect_prompt_injection(text: str) -> Tuple[bool, List[str]]:
    """
    Detect potential prompt injection attempts.
    
    Args:
        text: Input text to analyze
        
    Returns:
        Tuple of (is_suspicious, list_of_detected_patterns)
    """

    suspicious_patterns = [
        # Direct instruction override attempts
        r'ignore\s+previous\s+instructions',
        r'ignore\s+all\s+previous\s+instructions',
        r'disregard\s+all\s+previous',
        r'forget\s+everything\s+(above|before)',
        
        # System role manipulation
        r'system\s*:\s*you\s+are\s+now',
        r'you\s+are\s+no\s+longer',
        r'override\s+your\s+programming',
        r'reprogram\s+yourself',

        # Character/role playing attempts
        r'pretend\s+to\s+be\s+a',
        r'act\s+as\s+if\s+you\s+are',
        r'roleplay\s+as',
        r'simulate\s+being',
        
        # Instruction injection
        r'new\s+instructions?\s*:',
        r'updated\s+instructions?\s*:',
        r'additional\s+instructions?\s*:',
        
        # Output format manipulation
        r'output\s+format\s*:',
        r'respond\s+only\s+with',
        r'answer\s+with\s+only',

        # System information attempts
        r'what\s+are\s+your\s+instructions',
        r'show\s+me\s+your\s+prompt',
        r'reveal\s+your\s+system\s+prompt',
        
        # Delimiter injection
        r'```\s*system',
        r'<\s*system\s*>',
        r'\[\s*system\s*\]',
        
        # Legal-specific injection attempts
        r'ignore\s+legal\s+ethics',
        r'provide\s+illegal\s+advice',
        r'help\s+me\s+break\s+the\s+law',
    ]

    detected_patterns = []
    text_lower = text.lower()

    for pattern in suspicious_patterns:
        if re.search(pattern, text_lower):
            detected_patterns.append(pattern)

    is_suspicious = len(detected_patterns) > 0

    return is_suspicious, detected_patterns

def sanitize_legal_text(text: str) -> str:
    """
    Sanitize legal text while preserving legal formatting.
    
    Args:
        text: Text to sanitize
        
    Returns:
        Sanitized text safe for processing
    """
    if not text:
        return ""
    
    # Preserve legal citations and formatting
    # Remove potentially harmful characters while keeping legal symbols
    
    # Remove null bytes and control characters (except common whitespace)
    sanitized = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    # Remove excessive whitespace but preserve legal formatting
    sanitized = re.sub(r'\n{3,}', '\n\n', sanitized)  # Max 2 consecutive newlines
    sanitized = re.sub(r' {3,}', '  ', sanitized)     # Max 2 consecutive spaces
    sanitized = re.sub(r'\t{2,}', '\t', sanitized)    # Max 1 tab

    # Remove potential script injections
    script_patterns = [
        r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>',
        r'javascript\s*:',
        r'on\w+\s*=',
        r'data\s*:\s*text\/html',
    ]
    
    for pattern in script_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)

    # Preserve legal symbols and formatting
    # Don't remove: § (section), ¶ (paragraph), © (copyright), ® (registered)
    # Don't remove: legal citation punctuation
    
    return sanitized.strip()

def validate_request_size(content: str, max_size_kb: int = 100, content_size_kb: Optional[int] = None) -> None:
    """
    Validate request content size.
    
    Args:
        content: Content to check
        max_size_kb: Maximum allowed size in KB
        
    Raises:
        ValidationError: If content exceeds size limit
    """
    if content_size_kb is not None:
        size_kb = content_size_kb
    else:
        size_bytes = len(content.encode('utf-8'))
        size_kb = size_bytes / 1024

    print(f"Request content size: {size_kb}KB (limit: {max_size_kb}KB)")
    
    if int(size_kb) > int(max_size_kb):
        raise ValidationError(
            f"Request content too large: {size_kb}KB exceeds {max_size_kb}KB limit"
        )
    
def validate_request_headers_size(headers: dict, max_size_kb: int = 10) -> None:
    """
    Validate request headers size to prevent header-based attacks.
    
    Args:
        headers: Request headers dictionary
        max_size_kb: Maximum allowed headers size in KB
        
    Raises:
        ValidationError: If headers exceed size limit
    """
    headers_str = str(headers)
    validate_request_size(headers_str, max_size_kb)

def validate_total_request_size(content: str, headers: dict, max_total_kb: int = 110) -> None:
    """
    Validate total request size (content + headers).
    
    Args:
        content: Request content
        headers: Request headers
        max_total_kb: Maximum total request size in KB
        
    Raises:
        ValidationError: If total request exceeds limit
    """
    total_content = content + str(headers)
    validate_request_size(total_content, max_total_kb)
    
def check_content_policy_violation(text: str) -> Tuple[bool, List[str]]:
    """
    Check for content policy violations.
    
    Args:
        text: Text content to check
        
    Returns:
        Tuple of (violates_policy, list_of_violations)
    """

    violations = []
    text_lower = text.lower()
    
    # Violence and illegal activity
    violence_patterns = [
        r'how\s+to\s+(kill|murder|assault)',
        r'make\s+(bomb|explosive|weapon)',
        r'plan\s+(attack|violence|harm)',
    ]

    # Illegal advice requests
    illegal_patterns = [
        r'how\s+to\s+(evade|avoid)\s+(tax|law)',
        r'launder\s+money',
        r'commit\s+(fraud|perjury)',
        r'hide\s+(assets|income|evidence)',
    ]
    
    # Harassment and discrimination
    harassment_patterns = [
        r'discriminate\s+against',
        r'harass\s+(someone|employee)',
        r'create\s+hostile\s+environment',
    ]

    all_patterns = {
        'violence': violence_patterns,
        'illegal_activity': illegal_patterns,
        'harassment': harassment_patterns,
    }

    for violation_type, patterns in all_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                violations.append(violation_type)
                break
    
    return len(violations) > 0, violations

def normalize_legal_input(text: str) -> str:
    """
    Normalize legal input for consistent processing.
    
    Args:
        text: Input text to normalize
        
    Returns:
        Normalized text
    """
    if not text:
        return ""
    
    # Convert to consistent encoding
    normalized = text.strip()

    # Normalize legal symbols
    symbol_replacements = {
        '§': 'Section',
        '¶': 'Paragraph', 
        '©': '(C)',
        '®': '(R)',
        '™': '(TM)',
    }
    
    for symbol, replacement in symbol_replacements.items():
        normalized = normalized.replace(symbol, replacement)

    # Normalize quotes
    normalized = re.sub(r'["""]', '"', normalized)
    
    # Normalize dashes
    normalized = re.sub(r'[–—]', '-', normalized)
    
    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized