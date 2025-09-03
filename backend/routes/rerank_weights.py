import json
from fastapi import Depends, APIRouter, HTTPException
from pydantic import BaseModel
import logging

from redis_cache.redis_cache import cache

logger = logging.getLogger(__name__)

router = APIRouter()

EVAL_ALPHA = 0.75  # weight for retriever similarity
EVAL_BETA = 0.25   # weight for offline eval_score

try:
    raw_weights = cache.get("eval_rerank_weights")
    if raw_weights:
        parsed_weights = raw_weights if isinstance(raw_weights, dict) else json.loads(raw_weights)
        EVAL_ALPHA = float(parsed_weights.get("alpha", EVAL_ALPHA))
        EVAL_BETA = float(parsed_weights.get("beta", EVAL_BETA))
        logger.info("Loaded rerank weights from cache: alpha=%s beta=%s", EVAL_ALPHA, EVAL_BETA)
except Exception:
    logger.debug("No persisted rerank weights found or failed to load")

class RerankWeights(BaseModel):
    alpha: float
    beta: float

@router.get("/rerank-weights")
async def get_rerank_weights():
    """
    Return current rerank weights (alpha, beta).
    alpha = weight for retriever similarity
    beta  = weight for offline eval score
    """
    return {"alpha": EVAL_ALPHA, "beta": EVAL_BETA}

@router.post("/rerank-weights")
async def set_rerank_weights(payload: RerankWeights):
    """
    Set rerank weights at runtime. Values will be normalized so alpha+beta == 1.
    Validates inputs are within [0,1] and not both zero.
    Persists values to redis (key: eval_rerank_weights) for restart durability.
    """
    global EVAL_ALPHA, EVAL_BETA

    a = float(payload.alpha)
    b = float(payload.beta)

    if not (0.0 <= a <= 1.0 and 0.0 <= b <= 1.0):
        raise HTTPException(status_code=400, detail="alpha and beta must be between 0 and 1")
    
    s = a + b
    if s == 0:
        raise HTTPException(status_code=400, detail="alpha and beta cannot both be zero")
    
    EVAL_ALPHA = a / s
    EVAL_BETA = b / s

     # Persist to cache for durability
    try:
        cache.set("eval_rerank_weights", json.dumps({"alpha": EVAL_ALPHA, "beta": EVAL_BETA}))
    except Exception:
        logger.debug("Failed to persist rerank weights to cache")

    logger.info("Updated rerank weights -> alpha=%s beta=%s", EVAL_ALPHA, EVAL_BETA)
    return {"alpha": EVAL_ALPHA, "beta": EVAL_BETA}