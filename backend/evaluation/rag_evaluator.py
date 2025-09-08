import logging
import os
import pathlib
import re
import sys
import traceback
import statistics
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from services.openai_service import openai_service
from utils.token_calculator import count_tokens

logger = logging.getLogger(__name__)


def _extract_doc_text(doc: Any) -> str:
    """Defensive helper: extract readable text from various doc shapes."""
    try:
        if hasattr(doc, "page_content"):
            return getattr(doc, "page_content") or ""
        if isinstance(doc, dict):
            return doc.get("content") or doc.get("text") or doc.get("page_content") or ""
        return str(doc) or ""
    except Exception:
        return ""


def _normalize_doc_id(val: Any) -> str:
    """Normalize a doc identifier or filename to a canonical token form."""
    try:
        s = str(val)
        base = os.path.basename(s)
        stem = pathlib.Path(base).stem
        normalized = stem.strip().lower().replace(" ", "_")
        normalized = re.sub(r"[^a-z0-9_]", "", normalized)
        return normalized if normalized else s.strip().lower()
    except Exception:
        return str(val).strip().lower()


def compute_latency_stats(latencies_ms: Iterable[float]) -> Dict[str, float]:
    """Return median and p95 for a list/iterable of latencies in milliseconds."""
    lat_list = [float(x) for x in latencies_ms] if latencies_ms else []
    if not lat_list:
        return {"median_ms": 0.0, "p95_ms": 0.0}
    median = float(statistics.median(lat_list))
    p95 = float(np.percentile(lat_list, 95))
    return {"median_ms": median, "p95_ms": p95}


def compute_recall_at_k(
    retrieved_documents: List[Any],
    ground_truth_doc_ids: Optional[List[str]],
    k: int = 100,
) -> float:
    """
    Compute recall@k: (# ground-truth docs found in top-k) / (# ground-truth docs).
    Returns 0.0 if no ground-truth ids provided.
    """
    if not ground_truth_doc_ids:
        return 0.0
    rank_info = compute_retrieval_ranks(retrieved_documents, ground_truth_doc_ids=ground_truth_doc_ids)
    relevant_ranks = rank_info.get("relevant_ranks", [])
    found_in_k = sum(1 for r in relevant_ranks if (r is not None and r <= k))
    total_gt = len([x for x in (ground_truth_doc_ids or []) if x is not None])
    if total_gt == 0:
        return 0.0
    return float(found_in_k) / float(total_gt)


def compute_retrieval_ranks(
    retrieved_documents: List[Any],
    ground_truth_answer: Optional[str] = None,
    ground_truth_doc_ids: Optional[List[str]] = None,
    relevance_marker_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Heuristic per-doc relevance detection and ranking info.

    Returns:
      {
        "relevance_flags": [bool,...],
        "relevant_ranks": [1-based positions of relevant docs],
        "rank_of_first_relevant": int|None,
        "reciprocal_rank": float,
        "precision_at_1": float,
      }
    """
    flags: List[bool] = []
    ground_text = (ground_truth_answer or "").strip().lower()
    marker_fields = relevance_marker_fields or ["is_relevant", "relevance", "relevance_score", "score"]

    gt_ids = set(_normalize_doc_id(x) for x in (ground_truth_doc_ids or []) if x is not None)

    for doc in retrieved_documents:
        try:
            text = _extract_doc_text(doc).lower()
            is_rel = False

            # find candidate id from dict/object/metadata
            doc_id = None
            try:
                candidate = None
                if isinstance(doc, dict):
                    for k in ("id", "doc_id", "source_id", "source_file"):
                        if k in doc and doc.get(k):
                            candidate = str(doc.get(k))
                            break
                    if not candidate and isinstance(doc.get("metadata"), dict):
                        meta_tmp = doc.get("metadata") or {}
                        for k in ("id", "doc_id", "source_id", "source_file"):
                            if k in meta_tmp and meta_tmp.get(k):
                                candidate = str(meta_tmp.get(k))
                                break
                else:
                    if hasattr(doc, "metadata") and isinstance(getattr(doc, "metadata"), dict):
                        meta_tmp = getattr(doc, "metadata") or {}
                        for k in ("id", "doc_id", "source_id", "source_file"):
                            if k in meta_tmp and meta_tmp.get(k):
                                candidate = str(meta_tmp.get(k))
                                break

                if candidate:
                    doc_id = _normalize_doc_id(candidate)
            except Exception:
                doc_id = None

            if doc_id and gt_ids and doc_id in gt_ids:
                is_rel = True
                flags.append(True)
                continue

            # 1) ground-truth substring match (conservative)
            if not is_rel and ground_text:
                if len(ground_text) > 3:
                    if re.search(re.escape(ground_text), text):
                        is_rel = True
                else:
                    if ground_text in text:
                        is_rel = True

            # 2) metadata markers
            if not is_rel:
                meta = {}
                if hasattr(doc, "metadata"):
                    meta = getattr(doc, "metadata") or {}
                elif isinstance(doc, dict):
                    meta = doc.get("metadata") or doc

                for mf in marker_fields:
                    if isinstance(meta, dict) and mf in meta:
                        v = meta.get(mf)
                        if isinstance(v, bool):
                            is_rel = bool(v)
                        else:
                            try:
                                is_rel = float(v) > 0.0
                            except Exception:
                                is_rel = bool(v)
                        if is_rel:
                            break

            flags.append(bool(is_rel))
        except Exception:
            flags.append(False)

    relevant_ranks = [i + 1 for i, f in enumerate(flags) if f]
    rank_of_first_relevant = relevant_ranks[0] if relevant_ranks else None
    reciprocal_rank = (1.0 / rank_of_first_relevant) if rank_of_first_relevant else 0.0
    precision_at_1 = 1.0 if flags and flags[0] else 0.0

    return {
        "relevance_flags": flags,
        "relevant_ranks": relevant_ranks,
        "rank_of_first_relevant": rank_of_first_relevant,
        "reciprocal_rank": reciprocal_rank,
        "precision_at_1": precision_at_1,
    }


@dataclass
class EvaluationResult:
    """
    Container for per-query evaluation scores and simple metadata.
    Scores are normalized to 0-1.
    """
    retrieval_precision_at_3: float
    retrieval_precision_at_5: float
    answer_relevance: float
    answer_faithfulness: float
    overall_score: float

    # Extra info for debugging
    retrieved_doc_count: int
    answer_length_tokens: int
    evaluation_timestamp: str

    # New ranking signals for MRR / P@1
    precision_at_1: float = 0.0
    reciprocal_rank: float = 0.0
    rank_of_first_relevant: Optional[int] = None

    # Added recall and latency stats
    recall_at_100: float = 0.0
    retrieval_latency_median_ms: float = 0.0
    retrieval_latency_p95_ms: float = 0.0


class RAGEvaluator:
    """
    The main evaluation engine. Use evaluate_rag_response() to get per-question EvaluationResult.
    """

    def __init__(self):
        # sentence-transformers model for semantic similarity comparisons
        self.similarity_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("RAG Evaluator initialized with similarity model")

    async def evaluate_rag_response(
        self,
        user_id: str,
        question: str,
        retrieved_documents: List[Dict[str, Any]],
        generated_answer: str,
        ground_truth_answer: Optional[str] = None,
        ground_truth_doc_ids: Optional[List[str]] = None,
        retrieval_latencies_ms: Optional[Iterable[float]] = None,
    ) -> EvaluationResult:
        """
        Evaluate a complete RAG response and return EvaluationResult.

        retrieval_latencies_ms (optional): iterable of retrieval timings (ms) to compute median/p95.
        """
        try:
            logger.info(f"🔍 Evaluating RAG response for question: {question[:120]}...")

            # Retrieval evaluation (now accepts ground truth for ranking signals)
            retrieval_scores = self._evaluate_retrieval_quality(
                question,
                retrieved_documents,
                ground_truth_answer=ground_truth_answer,
                ground_truth_doc_ids=ground_truth_doc_ids,
            )

            # Answer relevance (LLM-as-judge or embedding compare)
            relevance_score = await self._evaluate_answer_relevance(
                user_id, question, generated_answer, ground_truth_answer
            )

            # Faithfulness (LLM-as-judge over sources)
            faithfulness_score = await self._evaluate_answer_faithfulness(
                user_id, generated_answer, retrieved_documents
            )

            # Overall score is mean of components (simple aggregate)
            overall_score = float(
                np.mean(
                    [
                        retrieval_scores.get("precision_at_3", 0.0),
                        retrieval_scores.get("precision_at_5", 0.0),
                        relevance_score,
                        faithfulness_score,
                    ]
                )
            )

            # latency stats (optional)
            latency_stats = compute_latency_stats(retrieval_latencies_ms) if retrieval_latencies_ms is not None else {"median_ms": 0.0, "p95_ms": 0.0}

            result = EvaluationResult(
                retrieval_precision_at_3=float(retrieval_scores.get("precision_at_3", 0.0)),
                retrieval_precision_at_5=float(retrieval_scores.get("precision_at_5", 0.0)),
                answer_relevance=float(relevance_score),
                answer_faithfulness=float(faithfulness_score),
                overall_score=overall_score,
                retrieved_doc_count=len(retrieved_documents),
                answer_length_tokens=count_tokens(generated_answer, "gpt-3.5-turbo"),
                evaluation_timestamp=datetime.utcnow().isoformat(),
            )

            # attach ranking signals if present
            result.precision_at_1 = float(retrieval_scores.get("precision_at_1", 0.0))
            result.reciprocal_rank = float(retrieval_scores.get("reciprocal_rank", 0.0))
            result.rank_of_first_relevant = retrieval_scores.get("rank_of_first_relevant")

            # attach recall + latency
            result.recall_at_100 = float(retrieval_scores.get("recall_at_100", 0.0))
            result.retrieval_latency_median_ms = float(latency_stats.get("median_ms", 0.0))
            result.retrieval_latency_p95_ms = float(latency_stats.get("p95_ms", 0.0))

            logger.info(f"✅ Evaluation complete. Overall score: {overall_score:.3f}")
            return result

        except Exception as e:
            exc_type, exc_value, exc_tb = sys.exc_info()
            if exc_tb:
                tb_list = traceback.extract_tb(exc_tb)
                last_frame = tb_list[-1]
                logger.error(f"❌ Error evaluating RAG response at {last_frame.filename}:{last_frame.lineno} - {e}")
                logger.error("Full traceback:\n" + "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
            else:
                logger.error(f"❌ Error evaluating RAG response: {e}")
            raise

    def _evaluate_retrieval_quality(
        self,
        question: str,
        retrieved_documents: List[Dict[str, Any]],
        ground_truth_answer: Optional[str] = None,
        ground_truth_doc_ids: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Compute retrieval quality and ranking signals.

        Returns dict with precision_at_1, precision_at_3, precision_at_5, rank_of_first_relevant, reciprocal_rank, recall_at_100.
        """
        if not retrieved_documents:
            logger.warning("No documents retrieved, precision = 0")
            return {
                "precision_at_1": 0.0,
                "precision_at_3": 0.0,
                "precision_at_5": 0.0,
                "rank_of_first_relevant": None,
                "reciprocal_rank": 0.0,
                "recall_at_100": 0.0,
            }

        # Semantic similarity flags
        try:
            question_embedding = self.similarity_model.encode([question])
        except Exception:
            question_embedding = None

        semantic_flags: List[bool] = []
        for doc in retrieved_documents:
            doc_text = _extract_doc_text(doc)
            if doc_text and question_embedding is not None:
                try:
                    doc_embedding = self.similarity_model.encode([doc_text])
                    similarity = float(np.dot(question_embedding[0], doc_embedding[0]))
                except Exception:
                    similarity = 0.0
                is_relevant_by_similarity = similarity > 0.5
                semantic_flags.append(bool(is_relevant_by_similarity))
                logger.debug(f"Doc similarity: {similarity:.3f}, relevant_by_sim: {is_relevant_by_similarity}")
            else:
                semantic_flags.append(False)

        # Heuristic ranking info using GT or metadata
        rank_info = compute_retrieval_ranks(
            retrieved_documents,
            ground_truth_answer=ground_truth_answer,
            ground_truth_doc_ids=ground_truth_doc_ids,
        )
        heuristic_flags = rank_info.get("relevance_flags", [])

        # Combine both signals (OR) to form final relevance decision
        combined_flags: List[bool] = []
        for i in range(len(retrieved_documents)):
            s = semantic_flags[i] if i < len(semantic_flags) else False
            h = heuristic_flags[i] if i < len(heuristic_flags) else False
            combined_flags.append(bool(s or h))

        def mean_bool_list(lst: List[bool]) -> float:
            return float(np.mean(lst)) if lst else 0.0

        precision_at_1 = 1.0 if combined_flags and combined_flags[0] else 0.0
        precision_at_3 = mean_bool_list(combined_flags[:3])
        precision_at_5 = mean_bool_list(combined_flags[:5])

        # recall@100 using ground-truth doc ids
        recall_at_100 = compute_recall_at_k(retrieved_documents, ground_truth_doc_ids, k=100)

        logger.debug(
            f"Retrieval quality combined: P@1={precision_at_1:.3f} P@3={precision_at_3:.3f} P@5={precision_at_5:.3f} recall@100={recall_at_100:.3f}"
        )

        return {
            "precision_at_1": float(precision_at_1),
            "precision_at_3": float(precision_at_3),
            "precision_at_5": float(precision_at_5),
            "rank_of_first_relevant": rank_info.get("rank_of_first_relevant"),
            "reciprocal_rank": float(rank_info.get("reciprocal_rank", 0.0)),
            "recall_at_100": float(recall_at_100),
        }

    async def _evaluate_answer_relevance(
        self,
        user_id: str,
        question: str,
        answer: str,
        ground_truth_answer: Optional[str] = None,
    ) -> float:
        """
        Grade how well the answer addresses the user's question.
        If ground truth is provided we use embedding similarity; otherwise LLM-as-judge.
        """
        if ground_truth_answer:
            try:
                answer_embedding = self.similarity_model.encode([answer])
                gt_embedding = self.similarity_model.encode([ground_truth_answer])
                similarity = float(np.dot(answer_embedding[0], gt_embedding[0]))
                relevance_score = max(0.0, min(1.0, similarity))
                logger.debug(f"Relevance via ground truth similarity: {similarity:.3f}")
                return relevance_score
            except Exception as e:
                logger.error(f"Embedding relevance failed: {e}")
                return self._simple_keyword_relevance(question, answer)
        else:
            # LLM-as-judge
            evaluation_prompt = f"""
Rate how well this answer addresses the user's question on a scale of 0-10.

User Question: {question}

Generated Answer: {answer}

Return only a number between 0 and 10.
"""
            try:
                result = await openai_service.simple_chat(
                    question=evaluation_prompt, user_id=user_id, model="gpt-3.5-turbo"
                )
                llm_response = result.get("response", "").strip()
                score = float(llm_response)
                relevance_score = max(0.0, min(1.0, score / 10.0))
                logger.debug(f"Relevance via LLM judge: {score:.1f} -> {relevance_score:.3f}")
                return relevance_score
            except Exception as e:
                logger.error(f"Error in LLM-as-judge evaluation: {e}")
                return self._simple_keyword_relevance(question, answer)

    # ...existing code...
    async def _evaluate_answer_faithfulness(
        self, user_id: str, answer: str, retrieved_documents: List[Dict[str, Any]],
        doc_map: Optional[List[str]] = None, prioritized_snippets: Optional[List[Dict[str, Any]]] = None
    ) -> float:
        """
        Grade whether the answer sticks to facts from retrieved documents.
        Uses LLM-as-judge with a combined source context. Accepts:
          - doc_map: optional list like ["Document 1: filename", ...] for clearer citations
          - prioritized_snippets: optional list of dicts {"src": ..., "snippet": ..., "score": ...}
        If LLM judge fails, falls back to deterministic heuristics:
          - section-number matching (e.g., 'Section 302')
          - named-entity overlap (simple capitalized sequence detection)
          - keyword overlap
        Returns score in [0.0, 1.0].
        """
        try:
            if not retrieved_documents and not prioritized_snippets:
                logger.warning("No source documents/snippets provided, cannot evaluate faithfulness")
                return 0.0

            # Build prioritized snippet list (prefer provided prioritized_snippets)
            snippets_for_prompt: List[Tuple[str, str]] = []  # list of (src, snippet)
            if prioritized_snippets:
                for s in prioritized_snippets:
                    # accept either dict with keys or simple tuple
                    if isinstance(s, dict):
                        src = s.get("src") or s.get("source") or s.get("source_file") or "unknown"
                        snippet = s.get("snippet") or s.get("text") or ""
                    elif isinstance(s, (list, tuple)) and len(s) >= 2:
                        src, snippet = s[0], s[1]
                    else:
                        continue
                    if snippet:
                        snippets_for_prompt.append((src, snippet))
            else:
                # fallback: extract short snippets from top retrieved_documents
                for doc in (retrieved_documents or [])[:5]:
                    doc_text = _extract_doc_text(doc)
                    src = None
                    try:
                        if isinstance(doc, dict):
                            src = doc.get("metadata", {}) and (doc.get("metadata").get("source") or doc.get("metadata").get("source_file"))
                            src = src or doc.get("id") or doc.get("source") or "unknown"
                        else:
                            meta = getattr(doc, "metadata", None) or {}
                            src = meta.get("source") or meta.get("source_file") or getattr(doc, "id", None) or "unknown"
                    except Exception:
                        src = "unknown"
                    if doc_text:
                        # pick first 800 chars as snippet
                        s = doc_text.strip().replace("\n", " ")
                        snippets_for_prompt.append((src, s[:800]))

            # Build source_context string with optional doc_map
            doc_map_text = "\n".join(doc_map) if doc_map else ""
            source_context_parts = []
            if doc_map_text:
                source_context_parts.append("DOCUMENT MAP:\n" + doc_map_text + "\n")
            for idx, (src, snip) in enumerate(snippets_for_prompt, start=1):
                source_context_parts.append(f"Document {idx} -- {src}:\n{snip}\n")
            source_context = "\n".join(source_context_parts)
            # Truncate to safe length for LLM judge
            max_source_chars = 4000
            if len(source_context) > max_source_chars:
                source_context = source_context[:max_source_chars].rsplit("\n", 1)[0] + "\n...[TRUNCATED]..."

            # LLM-as-judge prompt (0-10)
            faithfulness_prompt = f"""
                Rate how faithful this generated answer is to the provided source documents on a scale of 0-10.
                Use only the source documents provided. If the answer invents facts not present in the sources, score lower.

                Source Documents:
                {source_context}

                Generated Answer:
                {answer}

                Return only a number between 0 and 10 (integers or decimals allowed).
                """
            try:
                result = await openai_service.simple_chat(
                    question=faithfulness_prompt, user_id=user_id, model="gpt-3.5-turbo"
                )
                llm_response = (result.get("response", "") or "").strip()
                # attempt to parse number from LLM response
                score = None
                try:
                    # sometimes model returns "8/10" or "8 out of 10"
                    m = re.search(r"([0-9]+(?:\.[0-9]+)?)", llm_response)
                    if m:
                        score = float(m.group(1))
                except Exception:
                    score = None

                if score is not None:
                    faithfulness_score = max(0.0, min(1.0, score / 10.0))
                    logger.debug(f"Faithfulness via LLM judge: {score:.1f} -> {faithfulness_score:.3f}")
                    return faithfulness_score
                else:
                    logger.debug("LLM judge returned non-numeric response; falling back to deterministic checks.")
            except Exception as e:
                logger.error(f"Error in faithfulness LLM judge: {e}. Falling back to deterministic checks.")

            # Deterministic fallback checks

            # 1) Section-number matching: look for patterns like 'Section 302', 'sec. 302', 's.302', 'IPC 302'
            def _extract_sections(text: str) -> List[str]:
                if not text:
                    return []
                patterns = [
                    r"\bsection\s+(\d+)\b",
                    r"\bsec\.?\s+(\d+)\b",
                    r"\bs\.\s*(\d+)\b",
                    r"\bipc\s+section\s+(\d+)\b",
                    r"\bipc\s+(\d+)\b",
                ]
                found = set()
                low = text.lower()
                for p in patterns:
                    for m in re.finditer(p, low, flags=re.IGNORECASE):
                        try:
                            found.add(m.group(1))
                        except Exception:
                            continue
                return sorted(found)

            answer_sections = set(_extract_sections(answer))
            source_sections = set()
            for _, snip in snippets_for_prompt:
                source_sections.update(_extract_sections(snip))
            section_match_count = len(answer_sections & source_sections)
            section_score = 0.0
            if answer_sections:
                section_score = float(section_match_count) / float(len(answer_sections))

            # 2) Named-entity/simple proper-noun overlap (capitalized sequences)
            def _extract_proper_nouns(text: str) -> List[str]:
                if not text:
                    return []
                # crude heuristic: sequences of Capitalized words (length>=1)
                candidates = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", text)
                # filter tiny/common words (single-letter, common starts)
                filtered = [c.strip() for c in candidates if len(c.strip()) > 2]
                return list(dict.fromkeys(filtered))  # preserve order, deduplicate

            answer_entities = set(_extract_proper_nouns(answer))
            source_entities = set()
            for _, snip in snippets_for_prompt:
                source_entities.update(_extract_proper_nouns(snip))
            entity_matches = answer_entities & source_entities
            entity_score = 0.0
            if answer_entities:
                entity_score = float(len(entity_matches)) / float(len(answer_entities))

            # 3) Keyword overlap (more robust than previous simple check)
            stop_words = {
                "the", "is", "at", "which", "on", "and", "a", "to", "are", "as", "in", "of", "for",
                "by", "with", "that", "this", "be", "were", "was", "it", "from", "or", "an"
            }
            def _token_set(text: str) -> set:
                toks = re.findall(r"[A-Za-z0-9]+", (text or "").lower())
                toks = [t for t in toks if t not in stop_words and len(t) > 2]
                return set(toks)

            answer_tokens = _token_set(answer)
            source_tokens = set()
            for _, snip in snippets_for_prompt:
                source_tokens.update(_token_set(snip))
            token_overlap = 0.0
            if answer_tokens:
                token_overlap = float(len(answer_tokens & source_tokens)) / float(len(answer_tokens))

            # Combine deterministic signals
            # Give higher weight to section matches and entity overlap if present
            weights = {"section": 0.45, "entity": 0.25, "token": 0.30}
            deterministic_score = (
                weights["section"] * section_score
                + weights["entity"] * entity_score
                + weights["token"] * token_overlap
            )
            deterministic_score = max(0.0, min(1.0, deterministic_score))
            logger.debug(
                "Faithfulness fallback scores: section=%.3f entity=%.3f token=%.3f combined=%.3f",
                section_score, entity_score, token_overlap, deterministic_score,
            )
            return deterministic_score

        except Exception as e:
            logger.exception("Unexpected error during faithfulness evaluation: %s", e)
            return 0.0

    def _simple_keyword_relevance(self, question: str, answer: str) -> float:
        """
        Fallback: keyword overlap between question and answer.
        """
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        stop_words = {"the", "is", "at", "which", "on", "and", "a", "to", "are", "as", "in", "of", "for"}
        question_words -= stop_words
        answer_words -= stop_words
        if not question_words:
            return 0.5
        overlap = len(question_words & answer_words)
        relevance = overlap / len(question_words)
        return min(1.0, relevance)

    def _simple_faithfulness_check(self, answer: str, source_context: str) -> float:
        """
        Fallback: keyword overlap between answer and source context.
        """
        answer_words = set(answer.lower().split())
        source_words = set(source_context.lower().split())
        if not answer_words:
            return 0.0
        overlap = len(answer_words & source_words)
        faithfulness = overlap / len(answer_words)
        return min(1.0, faithfulness)


# Global instance for use across the application
rag_evaluator = RAGEvaluator()