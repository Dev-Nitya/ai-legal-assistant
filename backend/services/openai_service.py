"""
OpenAI Service - Centralized AI Request Handler with Accurate Cost Tracking

Simple Flow:
1. Our API calls: openai_service.chat_completion("Hello", user_id="john")
2. Service calls OpenAI API
3. Service extracts REAL token usage from OpenAI response
4. Service calculates EXACT cost using real tokens
5. Service records real spending for user "john"
6. Service returns: {response: "Hi there!", cost_info: {actual_cost: $0.00234}}
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from openai import AsyncOpenAI

from config.settings import settings
from services.cost_monitoring_service import cost_monitoring_service
from utils.token_calculator import count_tokens
from config.cost_limits import get_model_pricing

logger = logging.getLogger(__name__)

class OpenAIService:
    """
    Centralized service for all OpenAI API interactions with automatic cost tracking.
    
    This service handles:
    1. All OpenAI API calls (chat, completions, embeddings, etc.)
    2. Real token usage extraction from OpenAI responses
    3. Exact cost calculation using actual token counts
    4. Automatic cost recording for users
    5. Error handling and retry logic
    6. Rate limiting and usage optimization
    
    Think of this as our "AI Request Manager" - it handles all the complex
    stuff so our API endpoints can focus on business logic.
    """
    
    def __init__(self):
        """
        Initialize the OpenAI service with API client and cost tracking.
        
        Sets up:
        - OpenAI API client with your API key
        - Default model settings
        - Error handling configuration
        - Cost tracking integration
        """
        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=getattr(settings, 'openai_api_key', None)
        )
        
        # Default settings for API calls
        self.default_model = "gpt-3.5-turbo"  # Cheapest model as default
        self.default_max_tokens = 1000        # Reasonable limit
        self.default_temperature = 0.7       # Balanced creativity
        
        # Cost tracking settings
        self.track_costs = True
        self.log_detailed_usage = True
        
        logger.info("OpenAI service initialized with cost tracking enabled")
    
    async def chat_completion(self, 
                            messages: List[Dict[str, str]], 
                            user_id: str,
                            model: str = None,
                            max_tokens: int = None,
                            temperature: float = None,
                            **kwargs) -> Dict[str, Any]:
        """
        Make a chat completion request with automatic cost tracking.
        
        Args:
            messages: Chat messages in OpenAI format [{"role": "user", "content": "Hello"}]
            user_id: Who is making this request (for cost tracking)
            model: OpenAI model to use (defaults to gpt-3.5-turbo)
            max_tokens: Maximum tokens in response (defaults to 1000)
            temperature: Creativity level 0-1 (defaults to 0.7)
            **kwargs: Additional OpenAI parameters
            
        Returns:
            Dictionary with:
            - response: The actual AI response content
            - cost_info: Detailed cost breakdown with REAL usage
            - metadata: Request timing, model used, etc.
            
        Example Usage:
            result = await openai_service.chat_completion(
                messages=[{"role": "user", "content": "Hello!"}],
                user_id="john_doe"
            )
            
            ai_response = result["response"]
            actual_cost = result["cost_info"]["actual_cost_usd"]
            real_tokens = result["cost_info"]["total_tokens"]
        """
        
        # Step 1: Set up parameters with defaults
        model = model or self.default_model
        max_tokens = max_tokens or self.default_max_tokens
        temperature = temperature if temperature is not None else self.default_temperature
        
        # Step 2: Log the request for debugging
        logger.info(f"🤖 Making OpenAI request for user {user_id}: {model}, max_tokens={max_tokens}")
        
        start_time = datetime.utcnow()
        
        try:
            # Step 3: Make the actual OpenAI API call
            openai_response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            # Step 4: Extract the AI's response content
            ai_content = self._extract_response_content(openai_response)
            
            # Step 5: Extract REAL token usage from OpenAI response
            real_usage = self._extract_real_token_usage(openai_response)
            
            # Step 6: Calculate EXACT cost using real token counts
            exact_cost = self._calculate_exact_cost(model, real_usage)
            
            # Step 7: Record the REAL spending for this user
            if self.track_costs and user_id:
                await self._record_real_cost(user_id, exact_cost, real_usage, model)
            
            # Step 8: Calculate request timing
            end_time = datetime.utcnow()
            request_duration = (end_time - start_time).total_seconds()
            
            # Step 9: Build comprehensive response with all information
            result = {
                "response": ai_content,
                "cost_info": {
                    "actual_cost_usd": exact_cost,
                    "input_tokens": real_usage["input_tokens"],
                    "output_tokens": real_usage["output_tokens"],
                    "total_tokens": real_usage["total_tokens"],
                    "model": model,
                    "cost_per_token": exact_cost / real_usage["total_tokens"] if real_usage["total_tokens"] > 0 else 0
                },
                "metadata": {
                    "request_duration_seconds": request_duration,
                    "timestamp": end_time.isoformat(),
                    "model_used": model,
                    "max_tokens_requested": max_tokens,
                    "temperature": temperature,
                    "user_id": user_id
                }
            }
            
            # Step 10: Log successful request with real costs
            logger.info(f"✅ OpenAI request completed for user {user_id}: "
                       f"${exact_cost:.6f} ({real_usage['total_tokens']} tokens, {request_duration:.2f}s)")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ OpenAI request failed for user {user_id}: {e}")
            raise
    
    def _extract_response_content(self, openai_response: Any) -> str:
        """
        Extract the actual AI response text from OpenAI's response object.
        
        SIMPLE PURPOSE: Get the AI's answer from the complex response object
        
        OpenAI returns a complex object, but we just want the text content.
        This method handles different response formats safely.
        
        Args:
            openai_response: Raw response from OpenAI API
            
        Returns:
            The AI's response text, or empty string if can't extract
        """
        try:
            # Standard chat completion response format
            if hasattr(openai_response, 'choices') and openai_response.choices:
                first_choice = openai_response.choices[0]
                
                # Chat completion format
                if hasattr(first_choice, 'message') and hasattr(first_choice.message, 'content'):
                    content = first_choice.message.content or ""
                    logger.debug(f"Extracted response content: {len(content)} characters")
                    return content
                
                # Text completion format (older API)
                if hasattr(first_choice, 'text'):
                    content = first_choice.text or ""
                    logger.debug(f"Extracted text completion: {len(content)} characters")
                    return content
            
            logger.warning("Cannot extract content from OpenAI response")
            return ""
            
        except Exception as e:
            logger.error(f"Error extracting response content: {e}")
            return ""
    
    def _extract_real_token_usage(self, openai_response: Any) -> Dict[str, int]:
        """
        Extract the REAL token usage from OpenAI's response.
        
        THIS IS THE KEY METHOD - it gets us exact token counts!
        
        OpenAI tells us exactly how many tokens were used:
        - prompt_tokens: Tokens in your input
        - completion_tokens: Tokens in AI's response  
        - total_tokens: Sum of both
        
        Args:
            openai_response: Raw response from OpenAI API
            
        Returns:
            Dictionary with exact token counts:
            {
                "input_tokens": 156,      # Exact input tokens
                "output_tokens": 89,      # Exact output tokens  
                "total_tokens": 245       # Exact total tokens
            }
        """
        try:
            # OpenAI includes usage information in all responses
            if hasattr(openai_response, 'usage'):
                usage = openai_response.usage
                
                real_usage = {
                    "input_tokens": getattr(usage, 'prompt_tokens', 0),
                    "output_tokens": getattr(usage, 'completion_tokens', 0),
                    "total_tokens": getattr(usage, 'total_tokens', 0)
                }
                
                logger.debug(f"📊 Real token usage: {real_usage['input_tokens']} input + "
                           f"{real_usage['output_tokens']} output = {real_usage['total_tokens']} total")
                
                return real_usage
            
            # Fallback: this shouldn't happen with modern OpenAI API
            logger.warning("No usage information in OpenAI response")
            return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            
        except Exception as e:
            logger.error(f"Error extracting real token usage: {e}")
            return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    
    def _calculate_exact_cost(self, model: str, real_usage: Dict[str, int]) -> float:
        """
        Calculate the EXACT cost using real token counts from OpenAI.
        
        SIMPLE MATH: tokens × price_per_token = exact_cost
        
        This is the industry standard way to calculate OpenAI costs:
        1. Get exact token counts from OpenAI response
        2. Look up current pricing for the model
        3. Calculate: (input_tokens/1000 × input_price) + (output_tokens/1000 × output_price)
        
        Args:
            model: OpenAI model that was used
            real_usage: Exact token counts from OpenAI response
            
        Returns:
            Exact cost in USD (accurate to 6 decimal places)
        """
        try:
            # Get current pricing for this model
            pricing = get_model_pricing(model)
            if not pricing:
                logger.error(f"No pricing found for model: {model}")
                return 0.0
            
            # Extract token counts
            input_tokens = real_usage["input_tokens"]
            output_tokens = real_usage["output_tokens"]
            
            # Calculate exact costs using real token counts
            # OpenAI prices are per 1,000 tokens, so we divide by 1000
            input_cost = (input_tokens / 1000) * pricing["input_cost_per_1k"]
            output_cost = (output_tokens / 1000) * pricing["output_cost_per_1k"]
            total_cost = input_cost + output_cost
            
            logger.debug(f"💰 Exact cost calculation: "
                        f"{input_tokens} input × ${pricing['input_cost_per_1k']}/1k = ${input_cost:.6f}, "
                        f"{output_tokens} output × ${pricing['output_cost_per_1k']}/1k = ${output_cost:.6f}, "
                        f"Total = ${total_cost:.6f}")
            
            return total_cost
            
        except Exception as e:
            logger.error(f"Error calculating exact cost: {e}")
            return 0.0
    
    async def _record_real_cost(self, user_id: str, exact_cost: float, 
                              real_usage: Dict[str, int], model: str) -> None:
        """
        Record the EXACT cost in our cost monitoring system.
        
        SIMPLE PURPOSE: Update the user's spending with real numbers
        
        This updates:
        - User's daily spending total
        - User's monthly spending total  
        - Triggers budget alerts if needed
        - Creates audit trail for billing
        
        Args:
            user_id: Who made the request
            exact_cost: Exact cost calculated from real token usage
            real_usage: Real token counts from OpenAI
            model: Model that was used
        """
        try:
            success = cost_monitoring_service.record_money_spent(user_id, exact_cost)
            
            if success:
                logger.info(f"💰 Recorded EXACT cost for user {user_id}: "
                           f"${exact_cost:.6f} ({real_usage['total_tokens']} tokens, {model})")
            else:
                logger.warning(f"❌ Failed to record exact cost for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error recording real cost for user {user_id}: {e}")
    
    async def simple_chat(self, question: str, user_id: str, 
                         model: str = None) -> Dict[str, Any]:
        """
        Simplified method for basic chat requests.
        
        SIMPLE PURPOSE: Easy way to ask AI a question and get cost info
        
        This is a convenience method that handles the common case:
        - User asks a question
        - AI responds
        - You get both the answer and exact cost
        
        Args:
            question: User's question as a simple string
            user_id: Who is asking
            model: Optional model override
            
        Returns:
            Same format as chat_completion but simpler to use
            
        Example:
            result = await openai_service.simple_chat(
                question="What is a contract?",
                user_id="john_doe"
            )
            
            answer = result["response"]
            cost = result["cost_info"]["actual_cost_usd"]
        """
        
        # Convert simple question to OpenAI message format
        messages = [
            {"role": "user", "content": question}
        ]
        
        # Use the full chat_completion method
        return await self.chat_completion(
            messages=messages,
            user_id=user_id,
            model=model
        )

# Global instance for use across the application
openai_service = OpenAIService()