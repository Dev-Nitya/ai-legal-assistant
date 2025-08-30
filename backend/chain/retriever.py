from pathlib import Path
import re
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain.schema import Document
from typing import List, Dict, Optional, Any

from chain.loader import vectorstore

class LegalHybridRetriever:
    def __init__(self, vectorstore, documents: List[Document]):
        self.vectorstore = vectorstore
        self.documents = documents

        try:
            # Create BM25 retriever for keyword-based search
            self.bm25_retriever = BM25Retriever.from_documents(documents)
            self.has_bm25 = True
        except Exception as e:
            print(f"Warning: BM25 retriever not available: {e}")
            self.bm25_retriever = None
            self.has_bm25 = False

        # Create semantic retriever
        self.semantic_retriever = vectorstore.as_retriever(search_kwargs={"k": 10})

        # Create ensemble retriever combining both (if BM25 is available)
        if self.has_bm25:
            self.ensemble_retriever = EnsembleRetriever(
                retrievers=[self.bm25_retriever, self.semantic_retriever],
                weights=[0.4, 0.6]  # 40% keyword, 60% semantic
            )
        else:
            # Fallback to just semantic retriever
            self.ensemble_retriever = self.semantic_retriever

    def retrieve_with_filters(
        self,
        query: str,
        filters: Optional[Dict] = None,
        k: int = 5
    ) -> List[Document]:
        """Retrieve documents with metadata filtering"""

        # Get initial results from ensemble retriever
        if self.has_bm25:
            docs = self.ensemble_retriever.get_relevant_documents(query)
        else:
            docs = self.semantic_retriever.get_relevant_documents(query)

        # Apply metadata-based filtering if filters are provided
        if filters:
            docs = self._apply_filters(docs, filters)

        # Rerank documents for better relevance
        docs = self._rerank_documents(docs, query)

        return docs[:k]

    def _apply_filters(
        self,
        docs: List[Document],
        filters: Dict
    ) -> List[Document]:
        """Apply metadata-based filtering"""
        filtered_docs = []

        for doc in docs:
            include_doc = True

            # Document type filter
            if 'document_type' in filters:
                if doc.metadata.get('document_type') != filters['document_type']:
                    include_doc = False

            # Legal topic filter
            if 'legal_topics' in filters:
                doc_topics = doc.metadata.get('legal_topics', [])
                if not any(topic in doc_topics for topic in filters['legal_topics']):
                    include_doc = False

            # Section filter
            if 'sections' in filters:
                doc_sections = doc.metadata.get('extracted_sections', [])
                if not any(section in doc_sections for section in filters['sections']):
                    include_doc = False

            # Acts filter
            if 'acts' in filters:
                doc_acts = doc.metadata.get('extracted_acts', [])
                if not any(act in ' '.join(doc_acts) for act in filters['acts']):
                    include_doc = False

            if include_doc:
                filtered_docs.append(doc)

        return filtered_docs

    def _rerank_documents(self, docs: List[Document], query: str) -> List[Document]:
        """Rerank documents based on relevance scoring"""
        scored_docs = []

        for doc in docs:
            score = self._calculate_relevance_score(doc, query)
            scored_docs.append((doc, score))

        # sort by score (descending)
        scored_docs.sort(key = lambda x: x[1], reverse=True)

        return [doc for doc, score in scored_docs]

    def _calculate_relevance_score(self, doc: Document, query: str) -> float:
        """Calculate relevance score for a document"""
        score = 0.0
        content = doc.page_content.lower()
        query_lower = query.lower()

        # Extract phrase matching
        if query_lower in content:
            score += 2.0

        # Individual word matching
        """
        This will rewards documents that contain more of the query words.
            - If the doc contains all query words → higher boost.

            - If only a few words match → smaller boost.

            - If no words match → no boost.
        """
        query_words = query_lower.split()
        word_matches = sum(1 for word in query_words if word in content)
        score += (word_matches / len(query_words)) * 1.5

        # Section reference bonus
        if re.search(r'section\s+\d+', content):
            score += 0.5

        # Document type relevance
        """
        This is a domain aware boost
            - If the query is about criminal matters (mentions “criminal, police, arrest, bail”)
            - And the document is from the criminal or procedure code
            Then increase its ranking (+0.8) because it’s highly likely to be relevant.
        """
        doc_type = doc.metadata.get('document_type', '')
        if doc_type in ['criminal_code', 'procedure_code'] and any(
            word in query_lower for word in ['criminal', 'police', 'arrest', 'bail']
        ):
            score += 0.8

        return score
    
class QueryProcessor:
    """Preprocess queries to enhance retrieval"""

    @staticmethod
    def preprocess_query(query: str) -> Dict[str, Any]:
        """Extract intent and entities from query"""
        query_lower = query.lower()

        # Extract section references
        section_matches = re.findall(r'section\s+(\d+[a-z]*)', query_lower)

        # Extract act references
        act_matches = []
        act_patterns = {
            'ipc': 'Indian Penal Code',
            'crpc': 'Criminal Procedure Code',
            'constitution': 'Constitution of India',
            'evidence act': 'Evidence Act'
        }
        for pattern, full_name in act_patterns.items():
            if pattern in query_lower:
                act_matches.append(full_name)

        # Determine query intent
        intent = 'general'
        if any(word in query_lower for word in ['what is', 'explain', 'meaning']):
            intent = 'explanation'
        elif any(word in query_lower for word in ['similar case', 'precedent', 'judgment']):
            intent = 'case_search'
        elif any(word in query_lower for word in ['procedure', 'process', 'how to']):
            intent = 'procedural'

        # Determine legal domain
        legal_domain = 'general'
        if any(word in query_lower for word in ['murder', 'theft', 'criminal', 'police']):
            legal_domain = 'criminal'
        elif any(word in query_lower for word in ['marriage', 'divorce', 'family']):
            legal_domain = 'family'
        elif any(word in query_lower for word in ['contract', 'property', 'civil']):
            legal_domain = 'civil'

        return {
            'original_query': query,
            'processed_query': query_lower,
            'sections': section_matches,
            'acts': act_matches,
            'intent': intent,
            'legal_domain': legal_domain,
            'filters': {
                'legal_topics': [legal_domain] if legal_domain != 'general' else [],
                'acts': act_matches,
                'sections': section_matches
            }
        }
    
try:
    from chain.loader import vectorstore, docs
    enhanced_retriever = LegalHybridRetriever(vectorstore, docs)
    query_processor = QueryProcessor()
    print("Enhanced retriever initialized successfully with cached documents.")
except ImportError as e:
    print(f"Warning: Could not initialize enhanced retriever: {e}")
    print(f"Error details: {e}")
    enhanced_retriever = None
    query_processor = QueryProcessor()
except Exception as e:
    print(f"Warning: Could not initialize enhanced retriever: {e}")
    print(f"Error details: {e}")
    enhanced_retriever = None
    query_processor = QueryProcessor()