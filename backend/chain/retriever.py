from pathlib import Path
import re
import unicodedata
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain.schema import Document
from typing import List, Dict, Optional, Any
import numpy as np
from sentence_transformers import SentenceTransformer

from chain.loader import vectorstore

RERANK_MODEL_NAME = "all-MiniLM-L6-v2"

class LegalHybridRetriever:
    def __init__(self, vectorstore, documents: List[Document]):
        self.vectorstore = vectorstore
        self.documents = documents
        self._reranker_model = None
        self.reranker_model_name = RERANK_MODEL_NAME

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

        def _pick_representative_page(pages: List[Document], prefer_section: Optional[str] = None) -> Document:
            # prefer a page that contains the section token in content
            if prefer_section:
                tok = re.sub(r'[^0-9a-z]', '', prefer_section.lower())
                for p in pages:
                    if re.search(rf'\bsection\s{re.escape(tok)}\b', (p.page_content or "").lower()):
                        return p
                # then prefer a page whose page-level metadata matches
                for p in pages:
                    es = p.metadata.get("extracted_sections") or p.metadata.get("extracted_sections_norm") or p.metadata.get("aggregated_extracted_sections_norm") or ""
                    if isinstance(es, (list, tuple, set)):
                        meta_list = [str(x).lower() for x in es]
                    else:
                        meta_list = [x.strip().lower() for x in re.split(r'\s*(?:,|;|\||/|and)\s*', str(es)) if x.strip()]
                    if any(re.sub(r'[^0-9a-z]', '', m) == tok for m in meta_list):
                        return p
            # fallback to top-ranked page
            return pages[0]

        # Build representative list preserving rerank order and returning at most one page per source
        by_file = {}
        for d in docs:
            src = d.metadata.get("source_file") or d.metadata.get("source")
            by_file.setdefault(src, []).append(d)

        picked = []
        seen = set()
        preferred_section = None
        if filters and 'sections' in filters and filters.get('sections'):
            preferred_section = str(filters['sections'][0])

        for d in docs:
            src = d.metadata.get("source_file") or d.metadata.get("source")
            if src in seen:
                continue
            pages = by_file.get(src, [])
            rep = _pick_representative_page(pages, preferred_section)
            picked.append(rep)
            seen.add(src)
            if len(picked) >= k:
                break

        return picked[:k]

    def _apply_filters(
        self,
        docs: List[Document],
        filters: Dict
    ) -> List[Document]:
        """Apply metadata-based filtering.
        By default all provided filter criteria must match (AND).
        If filters contains "match_any_filter": True then a document is kept if it matches ANY filter (OR).
        """
        filtered_docs = []

        def _to_list(v):
            if v is None:
                return []
            if isinstance(v, (list, tuple, set)):
                return [str(x).strip().lower() for x in v if str(x).strip()]
            if isinstance(v, str):
                s = v.strip()
                if s == "":
                    return []
                parts = re.split(r'\s*(?:,|;|\||/|and)\s*', s)
                return [p.strip().lower() for p in parts if p.strip()]
            return [str(v).strip().lower()]

        def _normalize_section_tokens(tokens, content: Optional[str] = None):
            out = []
            for t in tokens:
                tok = re.sub(r'[^0-9a-z]', '', str(t).lower())
                if not tok:
                    continue
                if len(tok) >= 2:
                    out.append(tok)
                    continue
                # single-char token: include only when context confirms it's a section
                if content and re.search(rf'\b(?:section|sec\.?|s\.)\s*{re.escape(tok)}\b', content, re.IGNORECASE):
                    out.append(tok)
            return out

        # mode: OR vs AND
        match_any_mode = bool(filters.get("match_any_filter", True))

        for doc in docs:
            # collect per-filter match results for filters that are present
            match_results = []

            # document_type (exact match)
            if 'document_type' in filters:
                match_results.append(doc.metadata.get('document_type') == filters['document_type'])

            # legal_topics (any overlap)
            if 'legal_topics' in filters:
                doc_topics = _to_list(doc.metadata.get('legal_topics', []))
                filter_topics = [str(t).strip().lower() for t in filters.get('legal_topics', [])]
                match_results.append(bool(set(doc_topics) & set(filter_topics)))

            # sections (normalized exact tokens)
            if 'sections' in filters:
                # include both page-level and aggregated-per-document section tokens
                raw_doc_secs_page = doc.metadata.get('extracted_sections_norm') or doc.metadata.get('extracted_sections') or []
                raw_doc_secs_agg = doc.metadata.get('aggregated_extracted_sections_norm') or []
                doc_sections = _to_list(raw_doc_secs_page) + _to_list(raw_doc_secs_agg)
                # dedupe
                doc_sections = list(dict.fromkeys(doc_sections))
                doc_sections = _normalize_section_tokens(doc_sections, getattr(doc, "page_content", None))
                
                filter_secs = []
                for s in filters.get('sections', []):
                    if s is None:
                        continue
                    fs = re.sub(r'[^0-9a-z]', '', str(s).lower())
                    if fs:
                        filter_secs.append(fs)
                match_results.append(any(fs == ds for fs in filter_secs for ds in doc_sections) if filter_secs else False)

            # acts (substring / token match)
            if 'acts' in filters:
                 # include both page-level and aggregated-per-document act tokens/names
                raw_doc_acts_page = doc.metadata.get('extracted_acts_norm') or doc.metadata.get('extracted_acts') or []
                raw_doc_acts_agg = doc.metadata.get('aggregated_extracted_acts_norm') or []
                doc_acts_list = _to_list(raw_doc_acts_page) + _to_list(raw_doc_acts_agg)
                # dedupe while preserving order
                doc_acts_list = list(dict.fromkeys(doc_acts_list))
                doc_acts_text = " ".join(doc_acts_list)
                
                filter_acts = [str(a).strip().lower() for a in filters.get('acts', []) if a is not None]
                act_match = False
                for fa in filter_acts:
                    if fa in doc_acts_text or any(fa in a for a in doc_acts_list):
                        act_match = True
                        break
                match_results.append(act_match)

            # If no specific filter keys were present, keep doc
            if not match_results:
                include_doc = True
            else:
                include_doc = any(match_results) if match_any_mode else all(match_results)

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
    
    def hybrid_retrieve(self, query: str, k: int = 50) -> List[Document]:
        """
        Hybrid retrieval: combine lexical (BM25) and semantic retrievers, dedupe,
        then rerank the combined candidate set and return top-k Documents.
        """
        candidates = []

        # collect BM25 candidates if available
        if self.has_bm25 and getattr(self, "bm25_retriever", None):
            try:
                bm25_docs = self.bm25_retriever.get_relevant_documents(query)
            except Exception:
                print("Warning: BM25 retriever failed during hybrid retrieval.")
                bm25_docs = []
        else:
            bm25_docs = []

        # collect semantic candidates
        try:
            sem_docs = self.semantic_retriever.get_relevant_documents(query)
        except Exception:
            print("Warning: Semantic retriever failed during hybrid retrieval.")
            sem_docs = []

        # merge while preserving order: BM25 first then semantic (will be re-ranked)
        combined = bm25_docs + sem_docs

        # Deduplicate by a stable document key (prefer metadata.source_file / source)
        seen = set()
        uniq = []
        for d in combined:
            src = d.metadata.get("source_file") or d.metadata.get("source") or getattr(d, "id", None) or (d.page_content[:200] if getattr(d, "page_content", None) else None)
            key = str(src)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(d)

        if not uniq:
            return []

        # Rerank the unique candidates using existing scorer and return top-k
        try:
           reranked = self.rerank(uniq, query, top_k=k)
        except Exception:
            reranked = self._rerank_documents(uniq, query)
            
        return reranked[:k]
    
    def _ensure_reranker_loaded(self):
        """Load the SBERT model on first use (no-op if model unavailable)."""
        if self._reranker_model is not None:
            return
        if SentenceTransformer is None:
            # model library not available
            self._reranker_model = None
            return
        try:
            self._reranker_model = SentenceTransformer(self.reranker_model_name)
        except Exception:
            self._reranker_model = None

    def rerank(self, candidates: List[Document], query: str, top_k: Optional[int] = None, alpha: float = 0.5) -> List[Document]:
        """
        Strong semantic reranker using SBERT:
         - compute embedding for query and candidate pages
         - compute cosine similarity
         - combine SBERT similarity with existing heuristic score:
             final_score = alpha * semantic_sim + (1-alpha) * normalized_heuristic_score
         - return candidates sorted by final_score (descending)

        Simple terms: SBERT gives a semantic match score; we mix it with current heuristic
        score so both content match and domain heuristics matter.
        """
        if not candidates:
            return []
        
        self._ensure_reranker_loaded()
        if self._reranker_model is None:
            # fallback: no SBERT available — use existing heuristic reranker
            return self._rerank_documents(candidates, query)

        # build texts to embed (use page content or small snippet)
        texts = [(getattr(d, "page_content", "") or "")[:1500] for d in candidates]

        try:
            q_emb = self._reranker_model.encode([query], convert_to_numpy=True)[0]
            doc_embs = self._reranker_model.encode(texts, convert_to_numpy=True)
        except Exception:
            # embedding failed — fallback to existing heuristic reranker
            return self._rerank_documents(candidates, query)
        
        def cosine(a, b):
            da = np.linalg.norm(a)
            db = np.linalg.norm(b)
            if da == 0 or db == 0:
                return 0.0
            return float(np.dot(a, b) / (da * db))

        sem_sims = [cosine(q_emb, de) for de in doc_embs]

        heur_scores = [self._calculate_relevance_score(d, query) for d in candidates]
        min_h, max_h = min(heur_scores), max(heur_scores)

        heur_norm = []
        if max_h - min_h > 1e-6:
            heur_norm = [(s - min_h) / (max_h - min_h) for s in heur_scores]
        else:
            heur_norm = [0.0 for _ in heur_scores]

        final_scores = []
        for i, d in enumerate(candidates):
            sem = sem_sims[i]
            h = heur_norm[i]
            final = alpha * sem + (1.0 - alpha) * h
            final_scores.append((d, final))

        final_scores.sort(key=lambda x: x[1], reverse=True)
        ranked = [d for d, s in final_scores]
        if top_k:
            return ranked[:top_k]
        return ranked

class QueryProcessor:
    """Preprocess queries to enhance retrieval"""

    @staticmethod
    def preprocess_query(query: str) -> Dict[str, Any]:
        """Extract intent and entities from query"""

         # Defensive normalization: handle None, normalize unicode, replace smart quotes
        if query is None:
            query = ""
        q_norm = unicodedata.normalize("NFKC", str(query))
        q_norm = q_norm.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
        q_norm = " ".join(q_norm.split())

        query_lower = q_norm.lower()

        # Extract section references
        section_matches = re.findall(r'section\s+(\d+[a-z]*)', query_lower)

        # Extract act references
        act_matches = []
        def _norm_act(s: str) -> str:
            # lower, replace non-alnum with underscore, collapse multiples, strip underscores
            t = re.sub(r'[^a-z0-9]+', '_', s.lower())
            return re.sub(r'_+', '_', t).strip('_')
        
        act_patterns = {
            r'\b(?:ipc|indian penal code|penal code|45 of 1860|1860)\b': 'Indian Penal Code, 1860',
            r'\b(?:crpc|code of criminal procedure|criminal procedure code|1973)\b': 'Code of Criminal Procedure, 1973',
            r'\b(?:constitution|constitution of india)\b': 'Constitution of India',
            r'\b(?:evidence act|evidence)\b': 'Evidence Act'
        }

        for pat, full_name in act_patterns.items():
            if re.search(pat, query_lower):
                # include both human-readable and normalized token to match either storage style
                act_matches.append(full_name)
                act_matches.append(_norm_act(full_name))

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

        filters = {
            'legal_topics': [legal_domain] if legal_domain != 'general' else [],
            'acts': act_matches,
            'sections': section_matches
        }
        # Remove empty/falsey filter entries so downstream filtering is not overly restrictive.
        cleaned_filters = {k: v for k, v in filters.items() if v}

        return {
            'original_query': query,
            'processed_query': query_lower,
            'sections': section_matches,
            'acts': act_matches,
            'intent': intent,
            'legal_domain': legal_domain,
            'filters': cleaned_filters
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