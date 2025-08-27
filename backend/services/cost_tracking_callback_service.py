"""
Simple LangChain callback for automatic cost tracking.
"""

import logging
from typing import Any
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from services.cost_monitoring_service import cost_monitoring_service
from config.cost_limits import get_model_pricing

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

    def __init__(self, user_id: str):
        """
        Initialize callback for a specific user.
        
        Args:
            user_id: Who is using the agent (for cost tracking)
        """
        self.user_id = user_id
        logger.info(f"Initialized cost tracking callback for user {user_id}")

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """
        Called automatically after every LLM call.
        
        LangChain calls this method after each OpenAI request.
        We extract the real usage and record the cost.
        
        Args:
            response: LangChain LLM response with token usage
            **kwargs: Additional callback data
        """
        try:
            # Extract token usage from response
            if response.llm_output and 'token_usage' in response.llm_output:
                usage = response.llm_output['token_usage']
                
                # Get real token counts
                input_tokens = usage.get('prompt_tokens', 0)
                output_tokens = usage.get('completion_tokens', 0)
                total_tokens = usage.get('total_tokens', 0)

                # Get model name (default to gpt-3.5-turbo if not specified)
                model = response.llm_output.get('model_name', 'gpt-3.5-turbo')

                # Calculate exact cost
                exact_cost = self._calculate_cost(model, input_tokens, output_tokens)

                # Record the cost
                success = cost_monitoring_service.record_money_spent(self.user_id, exact_cost)

                if success:
                    logger.info(f"💰 Recorded ${exact_cost:.6f} for user {self.user_id} "
                               f"({total_tokens} tokens, {model})")
                else:
                    logger.warning(f"❌ Failed to record cost for user {self.user_id}")
                    
            else:
                logger.warning("No token usage in LLM response")
                
        except Exception as e:
            logger.error(f"Error in cost tracking callback: {e}")

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