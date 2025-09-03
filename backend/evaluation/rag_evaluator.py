import logging
import re
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from services.openai_service import openai_service
from utils.token_calculator import count_tokens

logger = logging.getLogger(__name__)


def _extract_doc_text(doc: Any) -> str:
    """
    Defensive helper: extract readable text from various doc shapes.
    """
    try:
        if hasattr(doc, "page_content"):
            return getattr(doc, "page_content") or ""
        if isinstance(doc, dict):
            return doc.get("content") or doc.get("text") or doc.get("page_content") or ""
        return str(doc) or ""
    except Exception:
        return ""


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
    gt_ids = set([str(x) for x in (ground_truth_doc_ids or []) if x is not None])

    for doc in retrieved_documents:
        try:
            text = _extract_doc_text(doc).lower()
            is_rel = False

            doc_id = None
            try:
                if isinstance(doc, dict):
                    for k in ("id", "doc_id", "source_id", "source_file"):
                        if k in doc and doc.get(k):
                            doc_id = str(doc.get(k))
                            break
                    # 2) Then check a 'metadata' field inside the dict (common shape)
                    if not doc_id and isinstance(doc.get("metadata"), dict):
                        meta_tmp = doc.get("metadata") or {}
                        for k in ("id", "doc_id", "source_id", "source_file"):
                            if k in meta_tmp and meta_tmp.get(k):
                                doc_id = str(meta_tmp.get(k))
                                break
                else:
                   # 3) If doc is an object with attribute 'metadata'
                   if hasattr(doc, "metadata") and isinstance(getattr(doc, "metadata"), dict):
                       meta_tmp = getattr(doc, "metadata") or {}
                       for k in ("id", "doc_id", "source_id", "source_file"):
                           if k in meta_tmp and meta_tmp.get(k):
                               doc_id = str(meta_tmp.get(k))
                               break
            except Exception:
                doc_id = None

            if doc_id and gt_ids and doc_id in gt_ids:
                is_rel = True
                flags.append(True)
                continue

            # 1) ground-truth substring match (conservative)
            if not is_rel:
                if ground_text:
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
    ) -> EvaluationResult:
        """
        Evaluate a complete RAG response and return EvaluationResult.
        """
        try:
            logger.info(f"🔍 Evaluating RAG response for question: {question[:120]}...")

            # Retrieval evaluation (now accepts ground truth for ranking signals)
            retrieval_scores = self._evaluate_retrieval_quality(
                question, 
                retrieved_documents, 
                ground_truth_answer=ground_truth_answer,
                ground_truth_doc_ids=ground_truth_doc_ids
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

            logger.info(f"✅ Evaluation complete. Overall score: {overall_score:.3f}")
            return result

        except Exception as e:
            # Detailed logging to aid debugging
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

        Returns dict with precision_at_1, precision_at_3, precision_at_5, rank_of_first_relevant, reciprocal_rank.
        """
        if not retrieved_documents:
            logger.warning("No documents retrieved, precision = 0")
            return {
                "precision_at_1": 0.0,
                "precision_at_3": 0.0,
                "precision_at_5": 0.0,
                "rank_of_first_relevant": None,
                "reciprocal_rank": 0.0,
            }

        # Semantic similarity flags (existing approach)
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
            ground_truth_doc_ids=ground_truth_doc_ids
        )
        heuristic_flags = rank_info.get("relevance_flags", [])

        # Combine both signals (OR) to form final relevance decision
        combined_flags: List[bool] = []
        for i in range(len(retrieved_documents)):
            s = semantic_flags[i] if i < len(semantic_flags) else False
            h = heuristic_flags[i] if i < len(heuristic_flags) else False
            combined_flags.append(bool(s or h))

        # Helper to compute mean of boolean list
        def mean_bool_list(lst: List[bool]) -> float:
            return float(np.mean(lst)) if lst else 0.0

        precision_at_1 = 1.0 if combined_flags and combined_flags[0] else 0.0
        precision_at_3 = mean_bool_list(combined_flags[:3])
        precision_at_5 = mean_bool_list(combined_flags[:5])

        logger.debug(f"Retrieval quality combined: P@1={precision_at_1:.3f} P@3={precision_at_3:.3f} P@5={precision_at_5:.3f}")

        return {
            "precision_at_1": float(precision_at_1),
            "precision_at_3": float(precision_at_3),
            "precision_at_5": float(precision_at_5),
            "rank_of_first_relevant": rank_info.get("rank_of_first_relevant"),
            "reciprocal_rank": float(rank_info.get("reciprocal_rank", 0.0)),
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

    async def _evaluate_answer_faithfulness(
        self, user_id: str, answer: str, retrieved_documents: List[Dict[str, Any]]
    ) -> float:
        """
        Grade whether the answer sticks to facts from retrieved documents.
        Uses LLM-as-judge with a combined source context.
        """
        if not retrieved_documents:
            logger.warning("No source documents, cannot evaluate faithfulness")
            return 0.0

        # Build a compact source context (limit size)
        source_context = ""
        for doc in retrieved_documents[:5]:
            doc_text = _extract_doc_text(doc)
            if doc_text:
                source_context += f"\n{doc_text}\n"

        faithfulness_prompt = f"""
Rate how faithful this generated answer is to the provided source documents on a scale of 0-10.

Source Documents:
{source_context[:2000]}

Generated Answer:
{answer}

Return only a number between 0 and 10.
"""
        try:
            result = await openai_service.simple_chat(
                question=faithfulness_prompt, user_id=user_id, model="gpt-3.5-turbo"
            )
            llm_response = result.get("response", "").strip()
            score = float(llm_response)
            faithfulness_score = max(0.0, min(1.0, score / 10.0))
            logger.debug(f"Faithfulness via LLM judge: {score:.1f} -> {faithfulness_score:.3f}")
            return faithfulness_score
        except Exception as e:
            logger.error(f"Error in faithfulness evaluation: {e}")
            return self._simple_faithfulness_check(answer, source_context)

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