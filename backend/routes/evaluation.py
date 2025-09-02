from fastapi import APIRouter, HTTPException, BackgroundTasks
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
from chain.retriever import enhanced_retriever
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
        
        # Use your existing retrieval system to find relevant documents
        retrieved_docs = enhanced_retriever.retrieve_with_filters(
            query=request.question,
            filters=None,
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

        # # Step 3: Convert retrieved docs to standard format for evaluation
        # # The RAG evaluator expects documents in a specific format
        # standardized_docs = []
        # for doc in retrieved_docs:
        #     if hasattr(doc, 'page_content'):
        #         # LangChain Document format
        #         standardized_docs.append({
        #             'content': doc.page_content,
        #             'metadata': getattr(doc, 'metadata', {})
        #         })
        #     elif isinstance(doc, dict):
        #         # Already in dict format
        #         content = doc.get('content', '') or doc.get('text', '') or doc.get('page_content', '')
        #         standardized_docs.append({
        #             'content': content,
        #             'metadata': doc.get('metadata', {})
        #         })
        #     else:
        #         # String or other format
        #         standardized_docs.append({
        #             'content': str(doc),
        #             'metadata': {}
        #         })

        # Step 4: Evaluate the quality of the response
        evaluation_result = await rag_evaluator.evaluate_rag_response(
            user_id=request.user_id,
            question=request.question,
            retrieved_documents=retrieved_docs,
            generated_answer=generated_answer,
            ground_truth_answer=request.ground_truth_answer if request.use_ground_truth else None
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
                "overall_score": float(evaluation_result.overall_score)
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

@router.post("/evaluate/batch", response_model=BatchEvaluationResponse)
async def evaluate_batch_questions(request: BatchEvaluationRequest):
    """
    Evaluate multiple questions from our test dataset.
    
    SIMPLE EXPLANATION:
    This endpoint runs a comprehensive test using our pre-defined
    legal questions. It's like giving your AI system a standardized
    exam and getting a detailed report card.
    
    HOW IT WORKS:
    1. Get test questions from our evaluation dataset
    2. Filter by category/difficulty if requested
    3. Run each question through the RAG system
    4. Evaluate each response
    5. Calculate summary statistics across all questions
    6. Return comprehensive results
    """
    
    logger.info(f"🔍 Starting batch evaluation with filters - category: {request.category}, difficulty: {request.difficulty}")
    start_time = datetime.utcnow()
    
    try:
        # Step 1: Get the questions to test
        all_questions = legal_eval_dataset.get_all_questions()
        
        # Filter by category if specified
        if request.category:
            questions_to_test = legal_eval_dataset.get_questions_by_category(request.category)
            logger.info(f"Filtered to {len(questions_to_test)} questions in category '{request.category}'")
        elif request.difficulty:
            questions_to_test = legal_eval_dataset.get_questions_by_difficulty(request.difficulty)
            logger.info(f"Filtered to {len(questions_to_test)} questions with difficulty '{request.difficulty}'")
        else:
            questions_to_test = all_questions
            logger.info(f"Testing all {len(questions_to_test)} questions")
        
        # Limit the number of questions if requested
        if len(questions_to_test) > request.max_questions:
            questions_to_test = questions_to_test[:request.max_questions]
            logger.info(f"Limited to {request.max_questions} questions")
        
        # Step 2: Evaluate each question
        individual_results = []
        all_scores = {
            "retrieval_precision_at_3": [],
            "retrieval_precision_at_5": [],
            "answer_relevance": [],
            "answer_faithfulness": [],
            "overall_score": []
        }
        category_scores = {}
        
        for i, question in enumerate(questions_to_test):
            logger.info(f"Evaluating question {i+1}/{len(questions_to_test)}: {question.id}")
            
            try:
                # Create single evaluation request
                single_request = SingleEvaluationRequest(
                    question=question.question,
                    user_id=request.user_id,
                    use_ground_truth=True,
                    ground_truth_answer=question.expected_answer
                )
                
                # Evaluate this question
                single_result = await evaluate_single_question(single_request)
                individual_results.append(single_result)
                
                # Collect scores for summary statistics
                eval_scores = single_result.evaluation_result
                for metric in all_scores.keys():
                    all_scores[metric].append(eval_scores[metric])
                
                # Collect scores by category
                if question.category not in category_scores:
                    category_scores[question.category] = {metric: [] for metric in all_scores.keys()}
                
                for metric in all_scores.keys():
                    category_scores[question.category][metric].append(eval_scores[metric])
                
            except Exception as e:
                logger.error(f"❌ Failed to evaluate question {question.id}: {e}")
                # Continue with other questions even if one fails
                continue
        
        # Step 3: Calculate summary statistics
        average_scores = {}
        for metric, scores in all_scores.items():
            if scores:  # Only calculate if we have scores
                average_scores[metric] = float(sum(scores) / len(scores))
            else:
                average_scores[metric] = 0.0
        
        # Calculate category breakdowns
        category_breakdown = {}
        for category, scores in category_scores.items():
            category_breakdown[category] = {}
            for metric, metric_scores in scores.items():
                if metric_scores:
                    category_breakdown[category][metric] = float(sum(metric_scores) / len(metric_scores))
                else:
                    category_breakdown[category][metric] = 0.0
        
        # Step 4: Create summary
        end_time = datetime.utcnow()
        total_time = (end_time - start_time).total_seconds()
        
        summary = {
            "total_processing_time_seconds": total_time,
            "average_processing_time_per_question": total_time / len(individual_results) if individual_results else 0,
            "successful_evaluations": len(individual_results),
            "failed_evaluations": len(questions_to_test) - len(individual_results),
            "best_performing_category": max(category_breakdown.keys(), 
                                          key=lambda k: category_breakdown[k]["overall_score"]) if category_breakdown else None,
            "worst_performing_category": min(category_breakdown.keys(), 
                                           key=lambda k: category_breakdown[k]["overall_score"]) if category_breakdown else None
        }
        
        # Step 5: Create the response with NumPy type conversion
        response_data = {
            "total_questions_tested": len(individual_results),
            "average_scores": convert_numpy_types(average_scores),
            "individual_results": [convert_numpy_types(result.dict()) for result in individual_results],
            "category_breakdown": convert_numpy_types(category_breakdown),
            "summary": convert_numpy_types(summary)
        }
        
        response = BatchEvaluationResponse(**response_data)
        
        logger.info(f"✅ Batch evaluation complete. Tested {len(individual_results)} questions. "
                   f"Average overall score: {average_scores.get('overall_score', 0):.3f}")
        
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