"""
Offline helper: compute per-document eval scores and persist in Redis.
"""

import json
import statistics
from typing import Dict, List

from redis_cache.redis_cache import cache
from evaluation.rag_evaluator import RAGEvaluator
from chain.retriever import enhanced_retriever
from config.settings import settings
from evaluation.eval_dataset import legal_eval_dataset

TOP_K = 10
OUTPUT_KEY_PREFIX = "eval_score:" # final key = eval_score:<doc_id>

def doc_id_for(doc) -> str:
    # Prefer an explicit id in metadata; fallback to source+page hash
    meta = getattr(doc, "metadata", {}) or {}
    doc_id = meta.get("id") or meta.get("source_file") or meta.get("source") or None
    if doc_id:
        return str(doc_id)
    # fallback: use source + page
    return f"{meta.get('source_file','unknown')}:{meta.get('page','-')}"

def save_eval_scores():
    print('Starting eval score computation...')
    # instantiate evaluator & retriever
    evaluator = RAGEvaluator()

    queries = legal_eval_dataset.get_all_questions()

    # per-doc scores accrual
    scores_by_doc: Dict[str, List[float]] = {}

    for q in queries:
        query_text = q.question
        # get top-k docs
        docs = enhanced_retriever.retrieve_with_filters(query_text, {}, TOP_K)
        for doc in docs:
            docid = doc_id_for(doc)
            # use evaluator to compute retrieval relevance for this (query, doc)
            try:
                score = evaluator._evaluate_retrieval_quality(query_text, doc)
                score = score['precision_at_5']
            except Exception:
                # fallback: use similarity if available
                score = float(getattr(doc, "score", 0.0) or doc.metadata.get("similarity", 0.0) or 0.0)

            scores_by_doc.setdefault(docid, []).append(float(score))
        
    print(scores_by_doc)

    # aggregate and persist to redis
    for docid, s_list in scores_by_doc.items():

        agg = float(statistics.mean(s_list))
        key = OUTPUT_KEY_PREFIX + docid
        
        try:
            cache.set(key, json.dumps({"score": agg}), expire=60 * 60 * 24 * 30)  # keep 30 days
            print(f"Persisted {key} = {agg}")
        except Exception as e:
            print(f"Failed to persist {key}: {e}")

save_eval_scores()