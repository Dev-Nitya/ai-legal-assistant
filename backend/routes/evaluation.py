from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Iterable, Tuple
import logging
import traceback
import sys
import numpy as np
from datetime import datetime
import time
import json

from evaluation.rag_evaluator import compute_latency_stats, rag_evaluator, EvaluationResult
from evaluation.eval_dataset import LegalEvalDataset

from chain.retriever import enhanced_retriever, query_processor
from services.openai_service import openai_service

router = APIRouter()
logger = logging.getLogger(__name__)

def convert_numpy_types(obj):
    """
    Convert NumPy types to native Python types for JSON serialization.
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj

# Request / Response models (kept simple & explicit)
class SingleEvaluationRequest(BaseModel):
    question: str
    user_id: str = "evaluator"
    use_ground_truth: bool = False
    ground_truth_answer: Optional[str] = None
    ground_truth_doc_ids: Optional[List[str]] = None

class BatchEvaluationRequest(BaseModel):
    category: Optional[str] = None
    difficulty: Optional[str] = None
    max_questions: int = 10
    user_id: str = "batch_evaluator"
    question_type: str

class EvaluationResponse(BaseModel):
    question: str
    generated_answer: str
    evaluation_result: Dict[str, Any]
    retrieved_documents_count: int
    processing_time_seconds: float
    timestamp: str

# Helper: normalize doc ids to canonical form for evaluation matching
def _normalize_doc_id(doc_id: Optional[str]) -> Optional[str]:
    if not doc_id:
        return None
    return doc_id.strip().lower()

# Helper: perform retrieval and rerank, return final retrieved_docs (ordered)

def retrieve_and_rerank(question: str, filters: Dict[str, Any]) -> Tuple[List[Any], List[float]]:
    """
    Replicates the retrieval and reranking flow from enhanced_chat_stream for true evaluation.
    """
    latencies = []
    t0 = time.time()

    # Step 1: Query analysis (already done before calling this function)
    # Step 2: Retrieval with filters (k=2, as in enhanced_chat_stream)
    try:
        if enhanced_retriever:
            relevant_docs = enhanced_retriever.retrieve_with_filters(
                query=question,
                filters=filters,
                k=2  # Match enhanced_chat_stream
            )
        else:
            # Fallback to basic retriever
            from chain.loader import vectorstore
            retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
            relevant_docs = retriever.get_relevant_documents(question)
    except Exception as e:
        logger.debug("Retrieval failed: %s", e)
        relevant_docs = []
    latencies.append((time.time() - t0) * 1000.0)

    # Step 3: Reranking (if enhanced_retriever, with alpha=0.75 and top_k=2)
    rerank_start = time.time()
    if enhanced_retriever and relevant_docs:
        try:
            relevant_docs = enhanced_retriever.rerank(
                relevant_docs, question, top_k=2, alpha=0.75  # Match EVAL_ALPHA in enhanced_chat
            )
        except Exception as e:
            logger.warning("Rerank failed: %s. Returning original docs.", e)
    latencies.append((time.time() - rerank_start) * 1000.0)

    # Step 4: Return docs and latencies
    return relevant_docs[:2], latencies  # Always return at most 2 docs, as in enhanced_chat_stream


# Helper: create evaluation prompt with strict grounding using doc_map + snippets
def make_evaluation_prompt(doc_map: List[str], full_context: str, question: str, evidence_threshold: float, max_context_chars: int = 18000) -> Tuple[str, str]:
    """
    Returns (evaluation_prompt, system_message)
    system_message enforces strict grounding when evidence >= threshold
    """
    doc_map_text = "\n".join(doc_map) if doc_map else "No documents."
    prompt = (
        "You are a helpful legal assistant. Answer the question based ONLY on the provided legal documents.\n\n"
        f"DOCUMENT MAP:\n{doc_map_text}\n\n"
        "DOCUMENT SNIPPETS (cite like Document 1):\n"
    )
    # Respect a max_context_chars cap to avoid huge prompts; truncate snippets if needed
    if len(full_context) > max_context_chars:
        full_context = full_context[:max_context_chars].rsplit("\n", 1)[0] + "\n...[TRUNCATED]..."
    prompt += full_context + "\n\n"
    prompt += f"QUESTION: {question}\n\n"
    prompt += "Answer concisely and include Document citations for every factual claim. If you do not find support in the documents, respond exactly: 'I cannot answer that from the provided documents.'"
    # system message enforces behavior; kept minimal but strict
    system_message = (
        "You are a helpful legal assistant. Use ONLY the information in the provided documents to answer. "
        "Cite Document numbers exactly (e.g., Document 1) for every factual claim. "
        "If the documents support a claim only partially, say 'Possibly' and cite supporting documents. "
        "If there is NO support in the provided documents for a claim, respond exactly: "
        "'I cannot answer that from the provided documents.' Do NOT invent facts."
    )
    return prompt, system_message

# Main single-question evaluation endpoint
@router.post("/evaluate/single", response_model=EvaluationResponse)
async def evaluate_single_question(request: SingleEvaluationRequest):
    logger.info("Starting single evaluation: %s", request.question[:120])
    start_time = datetime.utcnow()
    try:
        # Preprocess query
        query_analysis = query_processor.preprocess_query(request.question)
        filters = query_analysis.get("filters", {})

        # Retrieval + rerank
        retrieved_docs, retrieval_latencies = retrieve_and_rerank(request.question, filters)

        from routes.enhanced_chat import format_context

        context = format_context(retrieved_docs)
        # Optionally truncate context as in production
        max_context_length = 6000
        if len(context) > max_context_length:
            context = context[:max_context_length] + "\n... [Context truncated for performance]"

        # Build prompt (match production prompt)
        prompt = (
            "You are a helpful legal assistant. Answer the question based ONLY on the provided legal documents.\n\n"
            f"{context}\n\n"
            f"QUESTION: {request.question}\n\n"
            "Answer concisely and include Document citations for every factual claim. If you do not find support in the documents, respond exactly: 'I cannot answer that from the provided documents.'"
        )
        system_message = (
            "You are a helpful legal assistant. Use ONLY the information in the provided documents to answer. "
            "Cite Document numbers exactly (e.g., Document 1) for every factual claim. "
            "If the documents support a claim only partially, say 'Possibly' and cite supporting documents. "
            "If there is NO support in the provided documents for a claim, respond exactly: "
            "'I cannot answer that from the provided documents.' Do NOT invent facts."
        )

        # Normalize ground truth doc ids for evaluator if present
        normalized_ground_truth_doc_ids = None
        if request.use_ground_truth and request.ground_truth_doc_ids:
            normalized_ground_truth_doc_ids = [_normalize_doc_id(x) for x in request.ground_truth_doc_ids]

        # Generate the answer with LLM
        result = await openai_service.simple_chat(
            question=prompt,
            user_id=request.user_id,
            model="gpt-3.5-turbo",
            system_message=system_message,
            top_p=1.0
        )
        generated_answer = result.get("response", "")

        # Evaluate the answer using RAGEvaluator (reuses internal retrieval metrics)
        evaluation_result = await rag_evaluator.evaluate_rag_response(
            user_id=request.user_id,
            question=request.question,
            retrieved_documents=retrieved_docs,
            generated_answer=generated_answer,
            ground_truth_answer=request.ground_truth_answer if request.use_ground_truth else None,
            ground_truth_doc_ids=normalized_ground_truth_doc_ids if request.use_ground_truth else None,
            retrieval_latencies_ms=retrieval_latencies,
        )

        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()

        response = EvaluationResponse(
            question=request.question,
            generated_answer=generated_answer,
            evaluation_result={
                "retrieval_precision_at_3": float(evaluation_result.retrieval_precision_at_3),
                "retrieval_precision_at_5": float(evaluation_result.retrieval_precision_at_5),
                "answer_relevance": float(evaluation_result.answer_relevance),
                "answer_faithfulness": float(evaluation_result.answer_faithfulness),
                "overall_score": float(evaluation_result.overall_score),
                "precision_at_1": float(getattr(evaluation_result, "precision_at_1", 0.0)),
                "reciprocal_rank": float(getattr(evaluation_result, "reciprocal_rank", 0.0)),
                "rank_of_first_relevant": getattr(evaluation_result, "rank_of_first_relevant", None),
                "recall_at_100": float(getattr(evaluation_result, "recall_at_100", 0.0)),
                "retrieval_latency_median_ms": float(getattr(evaluation_result, "retrieval_latency_median_ms", 0.0)),
                "retrieval_latency_p95_ms": float(getattr(evaluation_result, "retrieval_latency_p95_ms", 0.0)),
            },
            retrieved_documents_count=len(retrieved_docs),
            processing_time_seconds=processing_time,
            timestamp=end_time.isoformat()
        )

        logger.info("Single evaluation complete. overall_score=%.3f", evaluation_result.overall_score)
        return response

    except Exception as e:
        exc_type, exc_value, exc_tb = sys.exc_info()
        if exc_tb:
            tb_list = traceback.extract_tb(exc_tb)
            last_frame = tb_list[-1]
            logger.error("Error in single question evaluation at %s:%s - %s", last_frame.filename, last_frame.lineno, e)
            logger.error("Full traceback:\n%s", "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
        else:
            logger.error("Error in single question evaluation: %s", e)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

# Batch evaluation reuses single evaluation for clarity; returns summary + samples
@router.post("/evaluate/batch")
async def evaluate_batch_questions(request: BatchEvaluationRequest):
    start_ts = int(time.time() * 1000)
    start_dt = datetime.utcnow()
    try:
        legal_eval_dataset = LegalEvalDataset(request.question_type)
        # Prepare question list
        if request.category:
            questions_to_test = legal_eval_dataset.get_questions_by_category(request.category)
        elif request.difficulty:
            questions_to_test = legal_eval_dataset.get_questions_by_difficulty(request.difficulty)
        else:
            questions_to_test = legal_eval_dataset.get_all_questions()

        limit = int(getattr(request, "max_questions", 10) or 10)
        if len(questions_to_test) > limit:
            questions_to_test = questions_to_test[:limit]

        individual_results = []
        collectors = {
            "retrieval_precision_at_3": [],
            "retrieval_precision_at_5": [],
            "answer_relevance": [],
            "answer_faithfulness": [],
            "overall_score": [],
            "processing_time_seconds": [],
            "retrieved_documents_count": [],
            "precision_at_1": [],
            "reciprocal_rank": [],
            "recall_at_100": [],
        }
        category_scores = {}

        for i, q in enumerate(questions_to_test):
            try:
                single_req = SingleEvaluationRequest(
                    question=q.question,
                    user_id=request.user_id,
                    use_ground_truth=True,
                    ground_truth_answer=getattr(q, "expected_answer", None),
                    ground_truth_doc_ids=getattr(q, "ground_truth_doc_ids", None)
                )
                single_resp = await evaluate_single_question(single_req)
                item = convert_numpy_types(single_resp.dict())
                individual_results.append(item)

                ers = item.get("evaluation_result", {}) or {}
                collectors["retrieval_precision_at_3"].append(float(ers.get("retrieval_precision_at_3", 0.0)))
                collectors["retrieval_precision_at_5"].append(float(ers.get("retrieval_precision_at_5", 0.0)))
                collectors["answer_relevance"].append(float(ers.get("answer_relevance", 0.0)))
                collectors["answer_faithfulness"].append(float(ers.get("answer_faithfulness", 0.0)))
                collectors["overall_score"].append(float(ers.get("overall_score", 0.0)))
                collectors["precision_at_1"].append(float(ers.get("precision_at_1", 0.0)))
                collectors["reciprocal_rank"].append(float(ers.get("reciprocal_rank", 0.0)))
                collectors["processing_time_seconds"].append(float(item.get("processing_time_seconds", 0.0)))
                collectors["retrieved_documents_count"].append(int(item.get("retrieved_documents_count", 0)))
                collectors["recall_at_100"].append(float(ers.get("recall_at_100", 0.0)))

                cat = getattr(q, "category", "unknown")
                category_scores.setdefault(cat, {
                    "retrieval_precision_at_3": [],
                    "retrieval_precision_at_5": [],
                    "answer_relevance": [],
                    "answer_faithfulness": [],
                    "overall_score": [],
                    "recall_at_100": [],
                })
                category_scores[cat]["retrieval_precision_at_3"].append(float(ers.get("retrieval_precision_at_3", 0.0)))
                category_scores[cat]["retrieval_precision_at_5"].append(float(ers.get("retrieval_precision_at_5", 0.0)))
                category_scores[cat]["answer_relevance"].append(float(ers.get("answer_relevance", 0.0)))
                category_scores[cat]["answer_faithfulness"].append(float(ers.get("answer_faithfulness", 0.0)))
                category_scores[cat]["overall_score"].append(float(ers.get("overall_score", 0.0)))
                category_scores[cat]["recall_at_100"].append(float(ers.get("recall_at_100", 0.0)))

            except Exception as e:
                logger.exception("Failed evaluating question %s: %s", getattr(q, "id", f"#{i}"), e)
                continue

        def safe_mean(lst):
            return float(sum(lst) / len(lst)) if lst else 0.0

        average_scores = {
            "retrieval_precision_at_3": safe_mean(collectors["retrieval_precision_at_3"]),
            "retrieval_precision_at_5": safe_mean(collectors["retrieval_precision_at_5"]),
            "answer_relevance": safe_mean(collectors["answer_relevance"]),
            "answer_faithfulness": safe_mean(collectors["answer_faithfulness"]),
            "overall_score": safe_mean(collectors["overall_score"]),
            "avg_processing_time_seconds": safe_mean(collectors["processing_time_seconds"]),
            "avg_retrieved_documents_count": safe_mean(collectors["retrieved_documents_count"]),
            "recall_at_100": safe_mean(collectors["recall_at_100"]),
        }

        # Derived metrics
        faithfulness_list = collectors["answer_faithfulness"]
        hallucination_rate = float(sum(1 for v in faithfulness_list if v < 0.5) / len(faithfulness_list)) if faithfulness_list else 0.0
        retrieval_coverage = float(sum(1 for c in collectors["retrieved_documents_count"] if c > 0) / len(collectors["retrieved_documents_count"])) if collectors["retrieved_documents_count"] else 0.0
        mrr = safe_mean(collectors.get("reciprocal_rank", []))
        p_at_1 = safe_mean(collectors.get("precision_at_1", []))
        global_latencies = compute_global_latency_stats(individual_results)

        metrics = {
            "precision_at_3": average_scores["retrieval_precision_at_3"],
            "precision_at_5": average_scores["retrieval_precision_at_5"],
            "mrr": mrr,
            "p_at_1": p_at_1,
            "recall_at_100": average_scores.get("recall_at_100", 0.0),
            "answer_relevance": average_scores["answer_relevance"],
            "answer_faithfulness": average_scores["answer_faithfulness"],
            "overall_score": average_scores["overall_score"],
            "hallucination_rate": hallucination_rate,
            "avg_response_time_ms": int(average_scores["avg_processing_time_seconds"] * 1000),
            "retrieval_coverage": retrieval_coverage,
            "raw_aggregates": average_scores,
            "retrieval_latency_global_p50_ms": float(global_latencies.get("global_p50_ms", 0.0)),
            "retrieval_latency_global_p95_ms": float(global_latencies.get("global_p95_ms", 0.0))
        }

        # prepare samples
        samples = []
        for idx, item in enumerate(individual_results):
            q_text = item.get("question", "") if isinstance(item, dict) else ""
            ans = item.get("generated_answer", "") if isinstance(item, dict) else ""
            ans_preview = (ans[:2000] + "...") if len(ans) > 2000 else ans
            eval_res = item.get("evaluation_result", {}) if isinstance(item, dict) else {}
            samples.append({
                "idx": idx,
                "question": q_text,
                "generated_answer_preview": ans_preview,
                "evaluation_result": eval_res,
                "retrieved_documents_count": item.get("retrieved_documents_count", 0),
                "retrieved_documents_preview": [],
                "processing_time_seconds": item.get("processing_time_seconds", 0.0),
            })

        # meta + response
        meta = {
            "limit": limit,
            "category": request.category,
            "difficulty": request.difficulty,
            "run_ts": start_ts,
            "run_started_at": start_dt.isoformat(),
            "rerank_weights": {"alpha": 0.6, "beta": 0.4}  # Fixed rerank weights
        }

        end_dt = datetime.utcnow()
        summary = {
            "total_processing_time_seconds": (end_dt - start_dt).total_seconds(),
            "average_processing_time_per_question": average_scores.get("avg_processing_time_seconds", 0.0),
            "successful_evaluations": len(individual_results),
            "failed_evaluations": len(questions_to_test) - len(individual_results),
        }

        response_payload = {
            "total_questions_tested": len(individual_results),
            "average_scores": convert_numpy_types(average_scores),
            "individual_results": individual_results,
            "category_breakdown": convert_numpy_types({k: {m: safe_mean(v) for m, v in vals.items()} for k, vals in category_scores.items()}),
            "summary": convert_numpy_types(summary),
            "metrics": metrics,
            "samples": samples,
            "meta": meta,
        }

        logger.info("Batch evaluation complete: tested=%s overall_score=%.3f", len(individual_results), average_scores.get("overall_score", 0.0))
        return JSONResponse(content=response_payload)

    except Exception as e:
        logger.exception("Batch evaluation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Batch evaluation failed: {str(e)}")
    
def compute_global_latency_stats(individual_results: List[Dict[str, Any]]) -> Dict[str, float]:
    vals: List[float] = []
    for item in individual_results:
        try:
            er = item.get("evaluation_result", {}) if isinstance(item, dict) else {}
            v = er.get("retrieval_latency_median_ms", None)
            if v is None:
                v = item.get("retrieval_latency_median_ms", None)
            if v is not None:
                vals.append(float(v))
        except Exception:
            continue
    if not vals:
        return {"global_p50_ms": 0.0, "global_p95_ms": 0.0}
    stats = compute_latency_stats(vals)
    return {"global_p50_ms": float(stats.get("median_ms", 0.0)), "global_p95_ms": float(stats.get("p95_ms", 0.0))}