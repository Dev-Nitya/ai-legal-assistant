"""
Cost monitoring service for tracking OpenAI usage and enforcing budgets.

This service provides comprehensive cost tracking and budget management
for OpenAI API usage across the entire application.

Key Features:
- Real-time cost tracking per user/session
- Budget enforcement with automatic cutoffs
- Cost analytics and reporting
- Alert system for budget thresholds
- Integration with Redis for fast lookups

Integration Points:
- Uses token_calculator.py for accurate cost estimation
- Integrates with cost_limits.py for budget configuration
- Stores data in Redis for fast access
- Provides middleware integration points
"""

import json
import logging
from time import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import redis

from config.settings import Settings
from config.cost_limits import (
    UserTier, BudgetLimits, BUDGET_TIERS, ALERT_THRESHOLDS,
    COST_ENFORCEMENT_CONFIG, COST_DATA_TTL, get_budget_for_tier
)
from utils.token_calculator import token_calculator

logger = logging.getLogger(__name__)

class BudgetPeriod(str, Enum):
    """
    Budget period definitions for different cost tracking intervals.
    
    Different periods allow for flexible budget management:
    - HOURLY: Prevents burst spending
    - DAILY: Most common for individual users
    - WEEKLY: Good for small teams
    - MONTHLY: Enterprise/organizational budgets
    """
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class AlertLevel(str, Enum):
    """
    Alert levels for budget notifications.
    
    Progressive alerting helps prevent budget overruns:
    - INFO: 50% of budget used
    - WARNING: 75% of budget used
    - CRITICAL: 90% of budget used
    - EMERGENCY: 100% budget exceeded
    """
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class CostRecord:
    """
    Individual cost record for tracking OpenAI API usage.
    
    Each API call generates a cost record for tracking and analytics.
    Stored in Redis with TTL for automatic cleanup.
    
    Fields Explanation:
    - user_id: Identifies which user made the request
    - session_id: Groups requests within a session
    - model: OpenAI model used (affects pricing)
    - input_tokens/output_tokens: Actual token usage
    - total_cost: Final cost in USD
    - timestamp: When the request was made
    - request_id: For tracing and debugging
    - endpoint: Which API endpoint was called
    """

    user_id: str
    session_id: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    timestamp: str
    request_id: Optional[str] = None
    endpoint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)
    
@dataclass
class BudgetStatus:
    """
    Current budget status for a user across all periods.
    
    Provides comprehensive view of budget utilization:
    - Current usage vs. limits for each period
    - Percentage utilization for alerts
    - Remaining budget for validation
    - Time until budget resets
    """
    user_id: str
    user_tier: UserTier
    hourly: Dict[str, float]
    daily: Dict[str, float]
    weekly: Dict[str, float]
    monthly: Dict[str, float]
    last_updated: str

    def get_most_restricitive_limit(self) -> Tuple[str, float]:
        """
        Get the most restrictive budget limit currently in effect.
        
        Returns:
            Tuple of (period_name, remaining_budget)
            
        Why This Is Important:
        - Determines if a request can proceed
        - Helps users understand their constraints
        - Enables smart budget management
        """

        limits = {
            "hourly": self.hourly.get("remaining", 0),
            "daily": self.daily.get("remaining", 0),
            "weekly": self.weekly.get("remaining", 0),
            "monthly": self.monthly.get("remaining", 0)
        }

        # Find the period with the lowest remaining budget
        most_restrictive = min(limits.items(), key=lambda x: x[1])
        return most_restrictive
    
    
class CostMonitoringService:
    """
    This is a "Budget Manager" for our app.
    
    It does 4 simple things:
    1. Checks if user can afford a request (before spending money)
    2. Records how much was actually spent (after the request)
    3. Sends alerts when budget is running low
    4. Stores all this data so it persists between requests
    """

    def __init__(self):
         # Connect to Redis (our "database" for fast budget lookups)
        self.redis_client = self._connect_to_redis()

    def can_user_afford_this_request(self, user_id, estimated_cost):
        """
        SIMPLE QUESTION: Can this user afford this AI request?
        
        This is like checking your bank balance before buying something.
        
        Steps:
        1. Get user's budget limits (how much they're allowed to spend)
        2. Get user's current spending (how much they've already spent)
        3. Calculate remaining budget
        4. Check if estimated cost fits within remaining budget
        """

        # Step 1: What are this user's spending limit?
        user_limits = self._get_user_spending_limits(user_id)

        # Step 2: How much has this user already spent?
        user_current_spending = self._get_user_current_spending(user_id)

        # Step 3: How much budget is left?
        daily_remaining = user_limits['daily'] - user_current_spending['daily']
        monthly_remaining = user_limits['monthly'] - user_current_spending['monthly']

        # Step 4: Can they afford this request?
        can_afford = (estimated_cost <= daily_remaining and 
                     estimated_cost <= monthly_remaining)
        
        if can_afford:
            return True, "User can afford the request"
        else:
            return False, f"Would exceed budget. Daily remaining: ${daily_remaining}"

    def record_money_spent(self, user_id, actual_cost):
        """
        SIMPLE ACTION: Record that money was spent.
        
        This is like updating your bank account after a purchase.
        
        Steps:
        1. Add the cost to user's daily spending
        2. Add the cost to user's monthly spending  
        3. Check if we should send any alerts
        """

        # Step 1 & 2: Update spending amounts
        self._add_to_user_spending(user_id, actual_cost)

        # Step 3: Should we warn the user?
        self._check_if_alerts_needed(user_id)

    def _get_user_spending_limits(self, user_id):
        """
        SIMPLE LOOKUP: What is this user allowed to spend?
        
        This is like looking up someone's credit limit.
        Different users have different limits based on their plan.
        """
        # Try to get custom limits from database
        custom_limits = self.redis_client.get(f"user_limits:{user_id}")
        
        if custom_limits:
            return json.loads(custom_limits)
        else:
            # Return default limits for new users
            return {"daily": 5.00, "monthly": 50.00}  # $5/day, $50/month
        
    def _get_user_current_spending(self, user_id):
        """
        SIMPLE LOOKUP: How much has this user already spent?
        
        This is like checking your bank account balance.
        We track spending by day and month.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        this_month = datetime.now().strftime("%Y-%m")

        # Get spending amount from Redis
        daily_spent = self.redis_client.get(f"spending:{user_id}:daily:{today}")
        monthly_spent = self.redis_client.get(f"spending:{user_id}:monthly:{this_month}")

        return {
            "daily": float(daily_spent) if daily_spent else 0.0,
            "monthly": float(monthly_spent) if monthly_spent else 0.0
        }
    
    def _add_to_user_spending(self, user_id, cost):
        """
        SIMPLE UPDATE: Add this cost to user's spending totals.
        
        This is like debiting money from their account.
        We update both daily and monthly totals.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        this_month = datetime.now().strftime("%Y-%m")
        
        # Add cost to daily total
        self.redis_client.incrbyfloat(f"spending:{user_id}:daily:{today}", cost)
        
        # Add cost to monthly total  
        self.redis_client.incrbyfloat(f"spending:{user_id}:monthly:{this_month}", cost)
        
        # Set expiration so old data gets cleaned up automatically
        self.redis_client.expire(f"spending:{user_id}:daily:{today}", 7 * 24 * 3600)  # 7 days
        self.redis_client.expire(f"spending:{user_id}:monthly:{this_month}", 90 * 24 * 3600)  # 90 days

    def _check_if_alerts_needed(self, user_id):
        """
        SIMPLE CHECK: Should we warn the user about their spending?
        
        This is like your bank sending you a "low balance" alert.
        We warn at 75% and 90% of budget used.
        """
        limits = self._get_user_spending_limits(user_id)
        current = self._get_user_current_spending(user_id)
        
        # Calculate percentage of daily budget used
        daily_percent = (current["daily"] / limits["daily"]) * 100
        
        # Send alerts at different thresholds
        if daily_percent >= 90:
            self._send_alert(user_id, "CRITICAL", f"90% of daily budget used")
        elif daily_percent >= 75:
            self._send_alert(user_id, "WARNING", f"75% of daily budget used")

    def _send_alert(self, user_id, level, message):
        """
        SIMPLE NOTIFICATION: Tell the user about their budget status.
        
        This is like sending a text message alert.
        For now, we just log it, but later we could email/SMS.
        """
        print(f"ALERT for {user_id}: {level} - {message}")
        
        # Store alert in Redis so UI can show it
        alert_data = {
            "user_id": user_id,
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

        alert_key = f"alert:{user_id}:{int(time.time())}"
        self.redis_client.setex(alert_key, 24 * 3600, json.dumps(alert_data))  # Keep for 24 hours

cost_monitoring_service = CostMonitoringService()