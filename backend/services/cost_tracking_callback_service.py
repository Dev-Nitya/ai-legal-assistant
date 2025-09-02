"""
Simple LangChain callback for automatic cost tracking.
"""

import json
import logging
from typing import Any, Dict, Optional
from langchain_core.outputs import LLMResult
from langchain.callbacks.base import BaseCallbackHandler

from services.cost_monitoring_service import cost_monitoring_service
from config.cost_limits import get_model_pricing
from redis_cache.redis_cache import cache

logger = logging.getLogger(__name__)

class CostTrackingCallback(BaseCallbackHandler):
    """
    simple callback that tracks OpenAI costs automatically.
    
    It will:
    1. Automatically track all LLM calls
    2. Extract real token usage from responses
    3. Calculate exact costs
    4. Record costs for the user
    """

    def __init__(self, user_id: str, request_id: Optional[str]):
        logger.info(f"Initialized cost tracking callback for user {user_id} and request {request_id}")
        self.user_id = user_id
        self.request_id = request_id

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        logger.info("Processing LLM response for user %s, kwargs=%s", self.user_id, kwargs)

        try:
            llm_output: Optional[dict] = None
            if hasattr(response, 'llm_output'):
                llm_output = getattr(response, 'llm_output')
            elif isinstance(response, dict):
                llm_output = response.get('llm_output')  or response.get("usage") or response.get("token_usage")

            if llm_output:
                usage = llm_output.get('token_usage') or llm_output.get('usage') or llm_output
                input_tokens = int(usage.get("prompt_tokens", 0))
                output_tokens = int(usage.get("completion_tokens", 0))
                total_tokens = int(usage.get("total_tokens", input_tokens + output_tokens))
                model = llm_output.get("model") or llm_output.get("model_name") or kwargs.get("model", "unknown")

                exact_cost = self._calculate_cost(model, input_tokens, output_tokens)
                logger.info("Calculated cost for user %s: $%f (tokens=%d)", self.user_id, exact_cost, total_tokens)

                recorded = cost_monitoring_service.record_money_spent(self.user_id, exact_cost)
                if not recorded:
                    logger.warning("Failed to record immediate cost for user %s", self.user_id)

            if self.request_id:
                try:
                    raw = cache.get(f"cost_est:{self.request_id}")
                    if raw:
                        est = json.loads(raw) if isinstance(raw, (str, bytes)) else raw
                        total_cost = est.get("total_cost_usd") or est.get("total_cost") or est.get("total_cost_usd", 0)
                        if total_cost:
                            logger.info("No token usage in LLM response; using middleware estimate for user %s: $%s", self.user_id, total_cost)
                            cost_monitoring_service.record_money_spent(self.user_id, float(total_cost))
                            return
                except Exception as e:
                    logger.debug("Failed to load cached estimate for request_id %s: %s", self.request_id, e)
        
        except Exception as e:
            logger.exception("Error in cost tracking callback on_llm_end: %s", e)

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate exact cost from real token usage."""
        try:
            pricing = get_model_pricing(model)
            if not pricing:
                return 0.0
            
            input_cost = (input_tokens / 1000) * pricing["input_cost_per_1k"]
            output_cost = (output_tokens / 1000) * pricing["output_cost_per_1k"]
            
            return input_cost + output_cost
            
        except Exception as e:
            logger.error(f"Error calculating cost: {e}")
            return 0.0