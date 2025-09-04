from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import asyncio
import traceback
import sys
import numpy as np
from datetime import datetime

# Import our evaluation components
from evaluation.rag_evaluator import rag_evaluator, EvaluationResult
from evaluation.eval_dataset import legal_eval_dataset, EvaluationQuestion

# Import your existing RAG system components
from chain.retriever import enhanced_retriever, query_processor
from services.openai_service import openai_service
from routes.enhanced_chat import enhanced_chat

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

class SingleEvaluationRequest(BaseModel):
    """
    Request format for evaluating a single question.
    
    SIMPLE PURPOSE: 
    This defines what information you need to send to test one question.
    """
    question: str
    user_id: str = "evaluator"
    use_ground_truth: bool = False
    ground_truth_answer: Optional[str] = None
    ground_truth_doc_ids: Optional[List[str]] = None

class BatchEvaluationRequest(BaseModel):
    """
    Request format for evaluating multiple questions at once.
    
    SIMPLE PURPOSE:
    This lets you run a bunch of tests at the same time,
    """
    category: Optional[str] = None          # Test only specific law category
    difficulty: Optional[str] = None       # Test only specific difficulty level
    max_questions: int = 10                # Limit how many questions to test
    user_id: str = "batch_evaluator"       # Who is running the batch test

class EvaluationResponse(BaseModel):
    """
    What you get back after an evaluation.
    """
    question: str                          # The question that was tested
    generated_answer: str                  # What your system answered
    evaluation_result: Dict[str, Any]      # The quality scores
    retrieved_documents_count: int         # How many docs were found
    processing_time_seconds: float        # How long it took
    timestamp: str                        # When the test was run

class BatchEvaluationResponse(BaseModel):
    """
        Results from testing multiple questions.
        
        SIMPLE PURPOSE:
        This is like a full report card with summary statistics
        across all the questions you tested.
    """
    total_questions_tested: int
    average_scores: Dict[str, float]       # Average quality scores
    individual_results: List[EvaluationResponse]  # Details for each question
    category_breakdown: Dict[str, Dict[str, float]]  # Scores by law category
    summary: Dict[str, Any]                # Overall summary statistics

@router.post("/evaluate/single", response_model=EvaluationResponse)
async def evaluate_single_question(request: SingleEvaluationRequest):
    """
    Evaluate a single question through your RAG system.

    HOW IT WORKS:
    1. Take the question from the request
    2. Run it through our retrieval system (find relevant docs)
    3. Generate an answer using our LLM
    4. Evaluate the quality using our evaluation framework
    5. Return detailed scores and metrics
    """

    logger.info(f"🔍 Starting single question evaluation: {request.question[:100]}...")
    start_time = datetime.utcnow()

    try:
        # Step 1: Run the question through your RAG system
        # This reuses your existing enhanced chat logic
        print("Running question through RAG pipeline...")
        
        query_analysis = query_processor.preprocess_query(request.question)

        # Use your existing retrieval system to find relevant documents
        retrieved_docs = enhanced_retriever.retrieve_with_filters(
            query=request.question,
            filters=query_analysis.get("filters", {}),
            k=5  # Get top 5 most relevant documents
        )

        # Convert retrieved documents to context text
        context_parts = []
        for i, doc in enumerate(retrieved_docs[:5]):  # Use top 5 documents
            # Handle different document formats from your retriever
            if hasattr(doc, 'page_content'):
                doc_text = doc.page_content
            elif isinstance(doc, dict):
                doc_text = doc.get('content', '') or doc.get('text', '') or doc.get('page_content', '')
            else:
                doc_text = str(doc)
            
            if doc_text.strip():  # Only add non-empty documents
                context_parts.append(f"Document {i+1}:\n{doc_text.strip()}")

        # Combine all document context
        full_context = "\n\n".join(context_parts) if context_parts else "No relevant documents found."

        # Step 2: Generate answer using your OpenAI service
        # We'll create a simple prompt for evaluation purposes
        evaluation_prompt = f"""You are a helpful legal assistant. Answer the question based ONLY on the provided legal documents.

        LEGAL DOCUMENTS:
        {full_context}

        QUESTION: {request.question}

        Instructions:
        1. Answer based only on the information in the provided documents
        2. If the documents don't contain enough information, say so
        3. Cite specific sections or document parts when possible
        4. Be accurate and concise

        ANSWER:"""
        # Generate the answer
        result = await openai_service.simple_chat(
            question=evaluation_prompt,
            user_id=request.user_id,
            model="gpt-3.5-turbo"  # Use consistent model for evaluation
        )
        
        generated_answer = result.get("response")

        # Step 4: Evaluate the quality of the response
        evaluation_result = await rag_evaluator.evaluate_rag_response(
            user_id=request.user_id,
            question=request.question,
            retrieved_documents=retrieved_docs,
            generated_answer=generated_answer,
            ground_truth_answer=request.ground_truth_answer if request.use_ground_truth else None,
            ground_truth_doc_ids=request.ground_truth_doc_ids
        )
        
        # Step 5: Calculate processing time
        end_time = datetime.utcnow()
        processing_time = (end_time - start_time).total_seconds()
        
        # Step 6: Format the response
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
            },
            retrieved_documents_count=len(retrieved_docs),
            processing_time_seconds=processing_time,
            timestamp=end_time.isoformat()
        )
        
        logger.info(f"✅ Single evaluation complete. Overall score: {evaluation_result.overall_score:.3f}")
        return response
        
    except Exception as e:
        # Get detailed error information including line number
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        # Get the line number where the error occurred
        if exc_traceback:
            tb_list = traceback.extract_tb(exc_traceback)
            # Get the last frame (most recent call)
            last_frame = tb_list[-1]
            error_line = last_frame.lineno
            error_filename = last_frame.filename
            error_function = last_frame.name
            
            logger.error(f"❌ Error in single question evaluation at line {error_line} in {error_function}(): {e}")
            logger.error(f"Full traceback:\n{''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))}")
        else:
            logger.error(f"❌ Error in single question evaluation: {e}")
            
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")

@router.post("/evaluate/batch")
async def evaluate_batch_questions(request: BatchEvaluationRequest):
    """
    Run a batch evaluation over the evaluation dataset and return a canonical,
    easy-to-store run payload.

    Return shape (JSON):
      - total_questions_tested: int
      - average_scores: dict (aggregated numeric metrics)
      - individual_results: list (per-question detailed results)
      - category_breakdown: dict (average metrics per category)
      - summary: dict (timing + counts)
      - metrics: dict (flat numeric metrics for dashboard)
      - samples: list (compact per-question objects suitable for DB/UI)
      - meta: dict (run configuration + reproducibility info)

    This replaces the previous implementation with a clearer, consistent output
    so the eval dashboard can persist useful runs.
    """
    import json
    import time
    from datetime import datetime

    start_ts = int(time.time() * 1000)
    start_dt = datetime.utcnow()
    try:
        # 1) Prepare questions
        all_questions = legal_eval_dataset.get_all_questions()
        if request.category:
            questions_to_test = legal_eval_dataset.get_questions_by_category(request.category)
        elif request.difficulty:
            questions_to_test = legal_eval_dataset.get_questions_by_difficulty(request.difficulty)
        else:
            questions_to_test = all_questions

        # enforce max_questions limit
        limit = int(getattr(request, "max_questions", 10) or 10)
        if len(questions_to_test) > limit:
            questions_to_test = questions_to_test[:limit]

        total = len(questions_to_test)

        # 2) Evaluate each question (reuse evaluate_single_question)
        individual_results = []
        # collectors for averages
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
                # single_resp is an EvaluationResponse pydantic model
                item = convert_numpy_types(single_resp.dict())
                individual_results.append(item)

                # collect numeric metrics if present (defensive)
                ers = item.get("evaluation_result", {}) or {}
                # safe-get with defaults
                collectors["retrieval_precision_at_3"].append(float(ers.get("retrieval_precision_at_3", 0.0)))
                collectors["retrieval_precision_at_5"].append(float(ers.get("retrieval_precision_at_5", 0.0)))
                collectors["answer_relevance"].append(float(ers.get("answer_relevance", 0.0)))
                collectors["answer_faithfulness"].append(float(ers.get("answer_faithfulness", 0.0)))
                collectors["overall_score"].append(float(ers.get("overall_score", 0.0)))
                collectors["precision_at_1"].append(float(ers.get("precision_at_1", 0.0)))
                collectors["reciprocal_rank"].append(float(ers.get("reciprocal_rank", 0.0)))
                collectors["processing_time_seconds"].append(float(item.get("processing_time_seconds", 0.0)))
                collectors["retrieved_documents_count"].append(int(item.get("retrieved_documents_count", 0)))

                # per-category aggregation
                cat = getattr(q, "category", "unknown")
                category_scores.setdefault(cat, {
                    "retrieval_precision_at_3": [],
                    "retrieval_precision_at_5": [],
                    "answer_relevance": [],
                    "answer_faithfulness": [],
                    "overall_score": [],
                })
                category_scores[cat]["retrieval_precision_at_3"].append(float(ers.get("retrieval_precision_at_3", 0.0)))
                category_scores[cat]["retrieval_precision_at_5"].append(float(ers.get("retrieval_precision_at_5", 0.0)))
                category_scores[cat]["answer_relevance"].append(float(ers.get("answer_relevance", 0.0)))
                category_scores[cat]["answer_faithfulness"].append(float(ers.get("answer_faithfulness", 0.0)))
                category_scores[cat]["overall_score"].append(float(ers.get("overall_score", 0.0)))

            except Exception as e:
                # Log and continue - individual failures shouldn't break the whole batch
                logger.exception("Failed evaluating question %s: %s", getattr(q, "id", f"#{i}"), e)
                continue

        # 3) Compute aggregated averages (safe division)
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
        }

        # 4) Category breakdown: mean per metric
        category_breakdown = {}
        for cat, data in category_scores.items():
            category_breakdown[cat] = {
                "retrieval_precision_at_3": safe_mean(data["retrieval_precision_at_3"]),
                "retrieval_precision_at_5": safe_mean(data["retrieval_precision_at_5"]),
                "answer_relevance": safe_mean(data["answer_relevance"]),
                "answer_faithfulness": safe_mean(data["answer_faithfulness"]),
                "overall_score": safe_mean(data["overall_score"]),
            }

        # 5) Build compact metrics for the dashboard (flat numerics)
        # Additional derived metrics:
        # - hallucination_rate: fraction where answer_faithfulness < 0.5
        faithfulness_list = collectors["answer_faithfulness"]
        hallucination_rate = float(sum(1 for v in faithfulness_list if v < 0.5) / len(faithfulness_list)) if faithfulness_list else 0.0
        retrieval_coverage = float(sum(1 for c in collectors["retrieved_documents_count"] if c > 0) / len(collectors["retrieved_documents_count"])) if collectors["retrieved_documents_count"] else 0.0
        mrr = safe_mean(collectors.get("reciprocal_rank", []))
        p_at_1 = safe_mean(collectors.get("precision_at_1", []))

        metrics = {
            "precision_at_3": average_scores["retrieval_precision_at_3"],
            "precision_at_5": average_scores["retrieval_precision_at_5"],
            "mrr": mrr,
            "p_at_1": p_at_1,
            "answer_relevance": average_scores["answer_relevance"],
            "answer_faithfulness": average_scores["answer_faithfulness"],
            "overall_score": average_scores["overall_score"],
            "hallucination_rate": hallucination_rate,
            "avg_response_time_ms": int(average_scores["avg_processing_time_seconds"] * 1000),
            "retrieval_coverage": retrieval_coverage,
            "raw_aggregates": average_scores,
        }

        # 6) Prepare samples: compact per-question objects for DB/UI
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
                # retrieved_documents_preview is not available in current single_eval - leave empty list
                "retrieved_documents_preview": [],
                "processing_time_seconds": item.get("processing_time_seconds", 0.0),
            })

        # 7) Meta: record run parameters for reproducibility
        meta = {
            "limit": limit,
            "category": request.category,
            "difficulty": request.difficulty,
            "run_ts": start_ts,
            "run_started_at": start_dt.isoformat(),
        }
        # try to include rerank weights if available in Redis (non-fatal)
        try:
            from redis_cache.redis_cache import cache as _cache
            raw_w = _cache.get("eval_rerank_weights")
            if raw_w:
                parsed_w = raw_w if isinstance(raw_w, dict) else json.loads(raw_w)
                meta["rerank_weights"] = {"alpha": float(parsed_w.get("alpha", 0.0)), "beta": float(parsed_w.get("beta", 0.0))}
        except Exception:
            pass

        # 8) Summary: counts and timing
        end_dt = datetime.utcnow()
        total_time_seconds = (end_dt - start_dt).total_seconds()
        summary = {
            "total_processing_time_seconds": total_time_seconds,
            "average_processing_time_per_question": average_scores.get("avg_processing_time_seconds", 0.0),
            "successful_evaluations": len(individual_results),
            "failed_evaluations": total - len(individual_results),
        }

        # 9) Compose response payload (keep legacy fields too for compatibility)
        response_payload = {
            "total_questions_tested": len(individual_results),
            "average_scores": convert_numpy_types(average_scores),
            "individual_results": individual_results,
            "category_breakdown": convert_numpy_types(category_breakdown),
            "summary": convert_numpy_types(summary),
            # canonical fields for dashboard/storage
            "metrics": metrics,
            "samples": samples,
            "meta": meta,
        }

        logger.info("✅ Batch evaluation complete: tested=%s overall_score=%.3f", len(individual_results), average_scores.get("overall_score", 0.0))
        return JSONResponse(content=response_payload)

    except Exception as e:
        logger.exception("Batch evaluation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Batch evaluation failed: {str(e)}")
        
    except Exception as e:
        # Get detailed error information including line number
        exc_type, exc_value, exc_traceback = sys.exc_info()
        
        # Get the line number where the error occurred
        if exc_traceback:
            tb_list = traceback.extract_tb(exc_traceback)
            # Get the last frame (most recent call)
            last_frame = tb_list[-1]
            error_line = last_frame.lineno
            error_filename = last_frame.filename
            error_function = last_frame.name
            
            logger.error(f"❌ Error in batch evaluation at line {error_line} in {error_function}(): {e}")
            logger.error(f"Full traceback:\n{''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))}")
        else:
            logger.error(f"❌ Error in batch evaluation: {e}")
            
        raise HTTPException(status_code=500, detail=f"Batch evaluation failed: {str(e)}")

@router.get("/evaluate/dataset/stats")
async def get_dataset_statistics():
    """
    Get statistics about our evaluation dataset.
    
    SIMPLE PURPOSE:
    This endpoint tells you what test questions are available,
    how they're distributed across categories and difficulty levels.
    Like looking at the table of contents of your test bank.
    """
    
    try:
        all_questions = legal_eval_dataset.get_all_questions()
        
        # Count questions by category
        category_counts = {}
        difficulty_counts = {}
        
        for question in all_questions:
            # Count by category
            if question.category in category_counts:
                category_counts[question.category] += 1
            else:
                category_counts[question.category] = 1
            
            # Count by difficulty
            if question.difficulty in difficulty_counts:
                difficulty_counts[question.difficulty] += 1
            else:
                difficulty_counts[question.difficulty] = 1
        
        return {
            "total_questions": len(all_questions),
            "questions_by_category": category_counts,
            "questions_by_difficulty": difficulty_counts,
            "available_categories": list(category_counts.keys()),
            "available_difficulties": list(difficulty_counts.keys())
        }
        
    except Exception as e:
        logger.error(f"Error getting dataset statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dataset stats: {str(e)}")

@router.get("/evaluate/dataset/questions/{category}")
async def get_questions_by_category(category: str):
    """
    Get all questions from a specific legal category.
    
    SIMPLE PURPOSE:
    This lets you see all the test questions for a particular
    area of law (like criminal law, contract law, etc.).
    
    WHEN YOU USE THIS:
    - Reviewing what questions are available for testing
    - Understanding the scope of each legal category
    - Planning targeted evaluations for specific law areas
    """
    
    try:
        questions = legal_eval_dataset.get_questions_by_category(category)
        
        if not questions:
            raise HTTPException(status_code=404, detail=f"No questions found for category: {category}")
        
        # Return question details without answers (for security)
        question_summaries = []
        for q in questions:
            question_summaries.append({
                "id": q.id,
                "question": q.question,
                "difficulty": q.difficulty,
                "keywords": q.keywords,
                "explanation": q.explanation
            })
        
        return {
            "category": category,
            "question_count": len(questions),
            "questions": question_summaries
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting questions for category {category}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get questions: {str(e)}")