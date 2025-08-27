"""
Legal domain-specific validators.

Contains validation logic specific to legal questions and content.
"""

import re
from typing import List
from schemas.validation import ValidationError, validate_text_length, validate_no_excessive_repetition

def validate_legal_question(question: str) -> str:
    """
    Comprehensive validation for legal questions.
    
    Validates length, content, and format of legal questions to ensure
    they are suitable for AI processing and won't cause issues.
    
    Args:
        question: Legal question text to validate
        
    Returns:
        Cleaned and validated question text
        
    Raises:
        ValidationError: If question fails validation
    """

    # Basic length and format validation 
    cleaned_question = validate_text_length(
        text=question,
        min_length=10,
        max_length=2000,
        field_name="Legal question"
    )

    # Check for excessive repetition
    validate_no_excessive_repetition(cleaned_question)

    # Check for minimum legal context
    if not _has_legal_context(cleaned_question):
        raise ValidationError(
            "Question should contain legal context or terminology"
        )
    
def _has_legal_context(text: str) -> bool:
    """
    Check if text contains legal context indicators.
    
    Args:
        text: Text to analyze
        
    Returns:
        True if text appears to have legal context
    """

    # Legal keywords that suggest a legal question (Indian legal system)
    legal_indicators = [
        # Legal concepts
        'law', 'legal', 'court', 'judge', 'advocate', 'lawyer', 'counsel', 'vakil',
        'contract', 'agreement', 'liability', 'damages', 'rights', 'obligation',
        'act', 'section', 'article', 'case', 'precedent', 'jurisdiction',
        
        # Legal processes
        'suit', 'petition', 'writ', 'litigation', 'trial', 'hearing', 'appeal',
        'filing', 'application', 'cross-examination', 'settlement', 'lok adalat',
        
        # Legal documents
        'will', 'trust', 'deed', 'lease', 'license', 'permit', 'patent',
        'trademark', 'copyright', 'memorandum of association', 'partnership deed',
        
        # Indian legal areas
        'criminal', 'civil', 'constitutional', 'corporate', 'employment',
        'family', 'property', 'consumer', 'labour', 'taxation',
        'arbitration', 'company law', 'service law',
        
        # Legal questions words
        'what are my rights', 'is it legal', 'can I', 'should I',
        'what happens if', 'how do I', 'what is the law',
        'kya main kar sakta hun', 'kya yeh legal hai'
    ]

    text_lower = text.lower()
    
    # Check for legal indicators
    for indicator in legal_indicators:
        if indicator in text_lower:
            return True
        
    # Check for question patterns that suggest legal inquiry (Indian context)
    legal_question_patterns = [
        r'\b(what|how|when|where|why|can|should|may|must|will)\b.*\b(law|legal|court|contract|right|liable|dhara|kanoon)\b',
        r'\bis\s+it\s+(legal|illegal|valid|enforceable|lawful)',
        r'\bdo\s+I\s+(have\s+to|need\s+to|have\s+the\s+right)',
        r'\bwhat\s+(are\s+my\s+rights|is\s+the\s+penalty|happens\s+if|section\s+says)',
        r'\bunder\s+(section|article|act|ipc|crpc|cpc)',
    ]

    for pattern in legal_question_patterns:
        if re.search(pattern, text_lower):
            return True
    
    return False

def validate_case_citation(citation: str) -> bool:
    """
    Validate Indian legal case citation format.
    
    Args:
        citation: Citation string to validate
        
    Returns:
        True if citation appears valid
    """
    # Indian citation patterns
    citation_patterns = [
        r'\(\d{4}\)\s+\d+\s+SCC\s+\d+',  # Supreme Court Cases (e.g., "(2020) 5 SCC 481")
        r'\d{4}\s+\d+\s+SCC\s+\d+',     # SCC without brackets
        r'AIR\s+\d{4}\s+SC\s+\d+',      # All India Reporter Supreme Court
        r'AIR\s+\d{4}\s+\w+\s+\d+',     # AIR High Court reports
        r'\d{4}\s+\(\d+\)\s+\w+LJ\s+\d+', # Law Journal citations
        r'\d{4}\s+\w+LR\s+\d+',         # Law Reports
        r'\(\d{4}\)\s+\d+\s+\w+\s+\d+', # General format with year
    ]

    for pattern in citation_patterns:
        if re.search(pattern, citation):
            return True
    
    return False

def extract_legal_entities(text: str) -> List[str]:
    """
    Extract legal entities from text.
    
    Args:
        text: Text to analyze
        
    Returns:
        List of potential legal entities found
    """
    entities = []
    
    # Entity patterns (Indian legal system)
    entity_patterns = {
        'acts': r'\b\w+\s+Act,?\s+\d{4}',  # e.g., "Companies Act, 2013"
        'ipc_sections': r'\bSection\s+\d+\s+IPC',  # Indian Penal Code sections
        'crpc_sections': r'\bSection\s+\d+\s+CrPC',  # Criminal Procedure Code
        'cpc_sections': r'\bSection\s+\d+\s+CPC',   # Civil Procedure Code
        'constitutional_articles': r'\bArticle\s+\d+',  # Constitutional articles
        'fundamental_rights': r'\bArticle\s+(14|15|16|17|18|19|20|21|22)',  # Fundamental rights articles
        'dpsp': r'\bArticle\s+(36|37|38|39|40|41|42|43|44|45|46|47|48|49|50|51)',  # DPSP articles
    }
    
    for entity_type, pattern in entity_patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities.extend(matches)
    
    return entities

def classify_legal_domain(text: str) -> str:
    """
    Classify the legal domain of a question.
    
    Args:
        text: Legal question text
        
    Returns:
        Identified legal domain or "general"
    """
    domain_keywords = {
        'contract': ['contract', 'agreement', 'breach', 'performance', 'consideration', 'offer', 'acceptance', 'sanvidha'],
        'tort': ['negligence', 'liability', 'damages', 'injury', 'fault', 'duty of care', 'tort', 'compensation'],
        'corporate': ['company', 'corporation', 'LLP', 'partnership', 'shareholder', 'director', 'companies act'],
        'employment': ['employee', 'employer', 'workplace', 'service', 'labour', 'industrial dispute', 'provident fund'],
        'property': ['property', 'real estate', 'immovable property', 'lease', 'rent', 'landlord', 'tenant', 'registration'],
        'criminal': ['crime', 'IPC', 'CrPC', 'FIR', 'chargesheet', 'bail', 'arrest', 'prosecution', 'sentence'],
        'family': ['marriage', 'divorce', 'maintenance', 'custody', 'adoption', 'hindu marriage act', 'personal law'],
        'constitutional': ['constitution', 'article', 'fundamental rights', 'directive principles', 'writ petition'],
        'taxation': ['income tax', 'GST', 'service tax', 'customs', 'excise', 'tax assessment', 'tax appeal'],
        'consumer': ['consumer protection', 'deficiency in service', 'unfair trade practice', 'consumer forum'],
        'arbitration': ['arbitration', 'conciliation', 'mediation', 'arbitral tribunal', 'award'],
        'service': ['government service', 'pension', 'promotion', 'disciplinary action', 'service rules']
    }

    text_lower = text.lower()
    domain_scores = {}

    for domain, keywords in domain_keywords.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        if score > 0:
            domain_scores[domain] = score
    
    if domain_scores:
        return max(domain_scores, key=domain_scores.get)
    
    return "general"