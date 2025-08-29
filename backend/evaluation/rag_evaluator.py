import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from sentence_transformers import SentenceTransformer
import json
from datetime import datetime

from services.openai_service import openai_service
from utils.token_calculator import count_tokens

logger = logging.getLogger(__name__)

@dataclass
class EvaluationResult:
    """
    Simple container for evaluation scores.
    
    Think of this like a report card with grades for different subjects.
    Each score is 0-1 (like a percentage: 0.85 = 85% good).
    """
    retrieval_precision_at_3: float # How many of top 3 docs were relevant?
    retrieval_precision_at_5: float # How many of top 5 docs were relevant?
    answer_relevance: float # Does answer match the question? (0-1)
    answer_faithfulness: float # Does answer stick to source facts? (0-1)
    overall_score: float # Average of all the above (0-1)

    # Extra info for debugging
    retrieved_doc_count: int
    answer_length_tokens: int
    evaluation_timestamp: str

class RAGEvaluator:
    """
    The main evaluation engine - like an automated teacher.
    HOW IT WORKS:
    1. We give it a question, retrieved docs, and generated answer
    2. It calculates quality scores using simple metrics
    3. It returns grades (0-1 scores) for different aspects
    4. We can track these scores over time
    """

    def __init__(self):
        """
        Initialize the evaluator with tools for measuring similarity.
        
        WHY WE NEED THIS:
        - SentenceTransformer: Measures how similar two pieces of text are
        - Like asking "How similar is this answer to the expected answer?"
        """
        # Load a model that can measure text similarity
        self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("RAG Evaluator initialized with similarity model")

    async def evaluate_rag_response(self, user_id:str, question: str, retrieved_documents: List[Dict[str, Any]],
                                    generated_answer: str, ground_truth_answer: Optional[str] = None) -> EvaluationResult:
        """
        Evaluate a complete RAG response (the main method you'll use)
        Args:
            question: What the user asked
            retrieved_documents: Documents your system found
            generated_answer: Answer your system generated
            ground_truth_answer: Known correct answer (optional, for testing)
            
        Returns:
            EvaluationResult with scores 0-1 for each quality metric
        """

        logger.info(f"🔍 Evaluating RAG response for question: {question[:100]}...")
        
        # Step 1: Evaluate retrieval quality
        # "Did we find relevant documents for this question?"
        retrieval_scores = self._evaluate_retrieval_quality(
            question, retrieved_documents
        )

        # Step 2: Evaluate answer relevance
        # "Does your answer actually address the question?"
        relevance_score = await self._evaluate_answer_relevance(
            user_id,
            question,
            generated_answer,
            ground_truth_answer
        )

        # Step 3: Evaluate answer faithfulness
        # "Did we stick to facts from the retrieved documents?"
        faithfulness_score = await self._evaluate_answer_faithfulness(
            user_id, generated_answer, retrieved_documents
        )

        # Step 4: Calculate overall score
        overall_score = float(np.mean([
            retrieval_scores['precision_at_3'],
            retrieval_scores['precision_at_5'],
            relevance_score,
            faithfulness_score
        ]))

        # Step 5: Create the final result
        result = EvaluationResult(
            retrieval_precision_at_3=float(retrieval_scores["precision_at_3"]),
            retrieval_precision_at_5=float(retrieval_scores["precision_at_5"]),
            answer_relevance=float(relevance_score),
            answer_faithfulness=float(faithfulness_score),
            overall_score=overall_score,
            retrieved_doc_count=len(retrieved_documents),
            answer_length_tokens=count_tokens(generated_answer, "gpt-3.5-turbo"),
            evaluation_timestamp=datetime.utcnow().isoformat()
        )
        
        logger.info(f"✅ Evaluation complete. Overall score: {overall_score:.3f}")
        return result

    def _evaluate_retrieval_quality(self, question: str, retrieved_documents: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Grade the quality of document retrieval.
        
        SIMPLE CONCEPT:
        If you ask "What is Section 302 IPC?" and we retrieve documents about:
        1. Section 302 IPC (murder law) ✅ RELEVANT
        2. Section 302 Companies Act ❌ NOT RELEVANT (wrong 302!)
        3. Section 299 IPC ❌ CLOSE BUT NOT RELEVANT
        
        We count how many of the top documents are actually relevant.
        
        HOW WE MEASURE:
        - Precision@3: Of the top 3 docs, how many are relevant?
        - Precision@5: Of the top 5 docs, how many are relevant?
        - Score = relevant_docs / total_docs (0.0 to 1.0)
        Args:
            question: User's original question
            retrieved_docs: List of documents our system found
            
        Returns:
            Dictionary with precision@3 and precision@5 scores
        """

        if not retrieved_documents:
            logger.warning("No documents retrieved, precision = 0")
            return {"precision_at_3": 0.0, "precision_at_5": 0.0}
        
        # We'll use semantic similarity to judge relevance
        # Convert question and documents to vectors for comparison
        question_embedding = self.similarity_model.encode([question])

        relevance_scores = []

        for doc in retrieved_documents:
            # Get document text
            doc_text = ""
            if isinstance(doc, dict):
                doc_text = doc.get("content", "") or doc.get("text", "") or doc.get('page_content', '')
            else:
                doc_text = str(doc)

            if doc_text:
                # Calculate how similar this document is to the question
                doc_embedding = self.similarity_model.encode([doc_text])
                similarity = np.dot(question_embedding[0], doc_embedding[0])
            
                # Consider document relevant if similarity > 0.5
                is_relevant = similarity > 0.5
                relevance_scores.append(is_relevant)

                logger.debug(f"Doc similarity: {similarity:.3f}, relevant: {is_relevant}")
            else:
                relevance_scores.append(False)

        # Calculate precision@3 and precision@5
        precision_at_3 = np.mean(relevance_scores[:3]) if len(relevance_scores) >= 3 else np.mean(relevance_scores)
        precision_at_5 = np.mean(relevance_scores[:5]) if len(relevance_scores) >= 5 else np.mean(relevance_scores)

        logger.debug(f"Retrieval quality: P@3={precision_at_3:.3f}, P@5={precision_at_5:.3f}")
        
        return {
            "precision_at_3": float(precision_at_3),
            "precision_at_5": float(precision_at_5)
        }
    
    async def _evaluate_answer_relevance(self, user_id:str, question: str, answer: str, ground_truth_answer: Optional[str] = None) -> float:
        """
        Grade how well the answer addresses the user's question.
        
        SIMPLE CONCEPT:
        If user asks "What is the punishment for murder in IPC Section 302?"
        - Good answer: "Life imprisonment or death penalty" ✅ 
        - Bad answer: "Section 302 deals with murder" ❌ (doesn't answer punishment)
        - Terrible answer: "Here's info about contracts" ❌ (completely irrelevant)
        
        HOW WE MEASURE:
        Method 1: If we have ground truth answer, compare similarity
        Method 2: Use LLM-as-judge to score relevance (0-10 scale)
        
        Args:
            question: User's original question
            generated_answer: Our system's answer
            ground_truth_answer: Known correct answer (if available)
            Returns:
            Relevance score from 0.0 to 1.0
        """

        if ground_truth_answer:
            # Method 1: Compare with known good answer using similarity
            answer_embedding = self.similarity_model.encode([answer])
            ground_truth_embedding = self.similarity_model.encode([ground_truth_answer])

            similarity = np.dot(answer_embedding[0], ground_truth_embedding[0])
            relevance_score = max(0.0, min(1.0, similarity))  # Clamp to [0, 1]

            logger.debug(f"Relevance via ground truth similarity: {similarity:.3f}")
            return relevance_score
        
        else:
            # Method 2: Use LLM to judge relevance
            evaluation_prompt = f"""
            Rate how well this answer addresses the user's question on a scale of 0-10.

            User Question: {question}

            Generated Answer: {answer}

            Scoring criteria:
            - 10: Perfect answer, directly addresses question completely
            - 8-9: Good answer, addresses main question with minor gaps
            - 6-7: Partial answer, addresses some aspects of question
            - 4-5: Weak answer, tangentially related to question
            - 2-3: Poor answer, barely related to question
            - 0-1: Irrelevant answer, doesn't address question at all

            Return only a number between 0 and 10.
            """

            try:
                result = await openai_service.simple_chat(
                    question=evaluation_prompt,
                    user_id=user_id,
                    model="gpt-3.5-turbo"
                )

                # Extract numeric score from response
                llm_response = result["response"].strip()
                score = float(llm_response)

                # Convert 0-10 scale to 0-1 scale
                relevance_score = max(0.0, min(1.0, score / 10.0))

                logger.debug(f"Relevance via LLM judge: {score:.1f} -> {relevance_score:.3f}")
                return relevance_score
            except Exception as e:
                logger.error(f"Error in LLM-as-judge evaluation: {e}")
                # Fallback: Use simple keyword matching
                return self._simple_keyword_relevance(question, answer)
            
    async def _evaluate_answer_faithfulness(self, 
                                            user_id:str,
                                            answer: str, 
                                            retrieved_documents: List[Dict[str, Any]]) -> float: 
        """
        Grade whether the answer sticks to facts from the source documents.
        
        SIMPLE CONCEPT (Preventing Hallucinations):
        If our documents say "Section 302 punishment is life imprisonment"
        - Faithful answer: "The punishment is life imprisonment" ✅
        - Unfaithful answer: "The punishment is 10 years in jail" ❌ (made up fact)
        - Unfaithful answer: "Also, the fine is 50,000 rupees" ❌ (not in sources)
        
        HOW WE MEASURE:
        Use LLM-as-judge to check if answer facts are supported by documents
        
        Args:
            generated_answer: Our system's answer
            retrieved_docs: Source documents our answer should be based on
            
        Returns:
            Faithfulness score from 0.0 to 1.0
        """
         
        if not retrieved_documents:
            logger.warning("No source documents, cannot evaluate faithfulness")
            return 0.0
        
        # Combine all source documents into context
        source_context = ""
        for doc in retrieved_documents[:5]:
            doc_text = ""
            if isinstance(doc, dict):
                doc_text = doc.get('content', '') or doc.get('text', '') or doc.get('page_content', '')
            else:
                doc_text = str(doc)
            
            if doc_text:
                source_context += f"\n{doc_text}\n"

        # Create evaluation prompt for faithfulness
        faithfulness_prompt = f"""
            Rate how faithful this generated answer is to the provided source documents on a scale of 0-10.

            Source Documents:
            {source_context[:2000]}  

            Generated Answer:
            {answer}

            Scoring criteria:
            - 10: All facts in answer are directly supported by source documents
            - 8-9: Most facts supported, minor unsupported details
            - 6-7: Some facts supported, some unsupported or inferred
            - 4-5: Mix of supported and unsupported facts
            - 2-3: Few facts supported, mostly unsupported
            - 0-1: Answer contains facts not found in sources (hallucination)

            Focus on factual accuracy, not writing style.
            Return only a number between 0 and 10.
            """
            
        try:
            result = await openai_service.simple_chat(
                question=faithfulness_prompt,
                user_id=user_id,
                model="gpt-3.5-turbo"
            )

            llm_response = result["response"].strip()
            score = float(llm_response)

            # Convert 0-10 scale to 0-1 scale
            faithfulness_score = max(0.0, min(1.0, score / 10.0))

            logger.debug(f"Faithfulness via LLM judge: {score:.1f} -> {faithfulness_score:.3f}")
            return faithfulness_score
        
        except Exception as e:
            logger.error(f"Error in faithfulness evaluation: {e}")
            # Fallback: Simple keyword overlap
            return self._simple_faithfulness_check(answer, source_context)


    def _simple_keyword_relevance(self, question: str, answer: str) -> float:
        """
        Simple fallback: check if answer contains keywords from question.
        
        This is a basic backup method if LLM evaluation fails.
        """
        question_words = set(question.lower().split())
        answer_words = set(answer.lower().split())
        
        # Remove common words
        stop_words = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'to', 'are', 'as', 'in', 'of', 'for'}
        question_words -= stop_words
        answer_words -= stop_words
        
        if not question_words:
            return 0.5  # Default if no meaningful words
        
        overlap = len(question_words & answer_words)
        relevance = overlap / len(question_words)
        
        return min(1.0, relevance)
    
    def _simple_faithfulness_check(self, answer: str, source_context: str) -> float:
        """
        Simple fallback: check keyword overlap between answer and sources.
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