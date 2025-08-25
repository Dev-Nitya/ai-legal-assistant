from typing import Dict
import re

def extract_legal_metadata(text: str, filename: str) -> Dict:
        """Extract legal-specific metadata from document text"""
        metadata = {
            'source_file': filename,
            'document_type': identify_document_type(filename, text),
            'jurisdiction': 'india',
            'extracted_sections': [],
            'extracted_acts': [],
            'legal_topics': [],
            'complexity_level': 'intermediate'
        }

        # Extract section references
        section_pattern = r'Section\s+(\d+[A-Z]*)'
        sections = re.findall(section_pattern, text, re.IGNORECASE)
        metadata['extracted_sections'] = list(set(sections))

        # Extract act references
        act_patterns = [
            r'Indian Penal Code',
            r'Code of Criminal Procedure',
            r'Constitution of India',
            r'Criminal Procedure Code',
            r'Hindu Marriage Act',
            r'Evidence Act',
        ]
        for pattern in act_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                metadata['extracted_acts'].append(pattern)

         # Identify legal topics
        topic_keywords = {
            'criminal': ['murder', 'theft', 'assault', 'criminal', 'police', 'fir'],
            'civil': ['contract', 'property', 'damages', 'civil', 'suit'],
            'constitutional': ['fundamental rights', 'directive principles', 'constitution'],
            'family': ['marriage', 'divorce', 'custody', 'maintenance'],
            'corporate': ['company', 'shares', 'directors', 'corporate']
        }
        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                metadata['legal_topics'].append(topic)

        return metadata
    
def identify_document_type(filename:str, text:str) -> str:
        """Identify the type of legal document"""
        filename_lower = filename.lower()
        text_lower = text.lower()

        if 'constitution' in filename_lower:
            return 'constitution'
        elif 'ipc' in filename_lower or 'penal code' in text_lower:
            return 'criminal_code'
        elif 'crpc' in filename_lower or 'criminal procedure' in text_lower:
            return 'procedure_code'
        elif 'evidence' in filename_lower:
            return 'evidence_act'
        elif 'judgment' in text_lower or 'petitioner' in text_lower:
            return 'case_law'
        else:
            return 'legal_document' 