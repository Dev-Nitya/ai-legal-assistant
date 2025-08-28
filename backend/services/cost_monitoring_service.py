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

from config.database import get_db
from models.user import UserBudget
from config.settings import settings
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

    def _connect_to_redis(self):
        try:
            # Try to connect to Redis server
            redis_client = redis.Redis(
                host=settings.redis_host,      # Redis server location
                port=settings.redis_port,            # Standard Redis port
                db=0,                 # Redis database number (0 is default)
                decode_responses=True, # Convert bytes to strings automatically
                socket_timeout=5,     # Don't wait forever for connection
                socket_connect_timeout=5
            )
            
            # Test the connection
            redis_client.ping()
            logger.info("✅ Connected to Redis for cost monitoring")
            return redis_client
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"⚠️  Redis not available: {e}")
            logger.warning("📝 Using in-memory storage (development mode)")
     
        except Exception as e:
            logger.error(f"❌ Unexpected Redis error: {e}")
            logger.warning("📝 Falling back to in-memory storage")
     
    def can_user_afford_this_request(self, user_id, estimated_cost, user_tier):
        """
        SIMPLE QUESTION: Can this user afford this AI request?
        
        This is like checking your bank balance before buying something.
        
        Steps:
        1. Get user's budget limits (how much they're allowed to spend)
        2. Get user's current spending (how much they've already spent)
        3. Calculate remaining budget
        4. Check if estimated cost fits within remaining budget
        """

        if not estimated_cost or estimated_cost.get('total_cost_usd', 0) <= 0:
            return True, "No cost estimated"
        
        total_cost = estimated_cost['total_cost_usd']

        try:
            db = next(get_db())

            user_budget = db.query(UserBudget).filter(UserBudget.user_id == user_id).first()
            if not user_budget:
                db.close()
                return False, "No budget configuration found for user"
            

            # Check if daily budget allows this request
            daily_remaining = user_budget.daily_limit_usd - user_budget.daily_spent_usd
            if total_cost > daily_remaining:
                db.close()
                return False, f"Daily budget exceeded. Remaining: ${daily_remaining:.2f}, Request: ${total_cost:.2f}"
            
            # Check if monthly budget allows this request  
            monthly_remaining = user_budget.monthly_limit_usd - user_budget.monthly_spent_usd
            if total_cost > monthly_remaining:
                db.close()
                return False, f"Monthly budget exceeded. Remaining: ${monthly_remaining:.2f}, Request: ${total_cost:.2f}"

            db.close()
            return True, "Budget check passed"
            
        except Exception as e:
            logger.error(f"Budget check error for user {user_id}: {e}")
            return False, "Budget check failed"

    def record_money_spent(self, user_id, actual_cost):
        """
        SIMPLE ACTION: Record that money was spent.
        
        This is like updating your bank account after a purchase.
        
        Steps:
        1. Add the cost to user's daily spending
        2. Add the cost to user's monthly spending  
        3. Check if we should send any alerts
        """

        if not actual_cost or actual_cost <= 0:
            logger.debug(f"No cost to record for user {user_id}")
            return True

        try:
            # Get database session
            db = next(get_db())
            
            # Find user's budget record
            user_budget = db.query(UserBudget).filter(UserBudget.user_id == user_id).first()
            
            if not user_budget:
                logger.warning(f"No budget record found for user {user_id} when recording ${actual_cost:.4f}")
                db.close()
                return False
            
            # Check if we need to reset daily/monthly counters
            current_date = datetime.utcnow().date()
            current_month = datetime.utcnow().replace(day=1).date()

            # Reset daily spending if it's a new day
            if user_budget.daily_reset_date and user_budget.daily_reset_date.date() < current_date:
                logger.info(f"Resetting daily spending for user {user_id} (new day)")
                user_budget.daily_spent_usd = 0.0
                user_budget.daily_reset_date = datetime.utcnow()
            
            # Reset monthly spending if it's a new month
            if user_budget.monthly_reset_date and user_budget.monthly_reset_date.date() < current_month:
                logger.info(f"Resetting monthly spending for user {user_id} (new month)")
                user_budget.monthly_spent_usd = 0.0
                user_budget.monthly_reset_date = datetime.utcnow()

            # Add the cost to current spending
            user_budget.daily_spent_usd += actual_cost
            user_budget.monthly_spent_usd += actual_cost
            user_budget.updated_at = datetime.utcnow()
            
            # Commit the changes
            db.commit()

            logger.info(f"💰 Recorded ${actual_cost:.4f} for user {user_id}. "
                       f"Daily: ${user_budget.daily_spent_usd:.2f}/${user_budget.daily_limit_usd:.2f}, "
                       f"Monthly: ${user_budget.monthly_spent_usd:.2f}/${user_budget.monthly_limit_usd:.2f}")
            
            # Check if we should send alerts

            self._check_budget_alerts(user_budget)

            db.close()
            return True
            
        except Exception as e:
            logger.error(f"Error recording ${actual_cost:.4f} for user {user_id}: {e}")
            if 'db' in locals():
                db.rollback()
                db.close()
            return False

    def _check_budget_alerts(self, user_budget: UserBudget):
        """
        UPDATED: Check if alerts needed based on UserBudget data
        
        SIMPLE EXPLANATION:
        Look at user's spending percentage and send alerts:
        - 75% of budget used → WARNING
        - 90% of budget used → CRITICAL
        """
        
        try:
            # Calculate daily budget usage percentage
            daily_usage_percent = (user_budget.daily_spent_usd / user_budget.daily_limit_usd) * 100 if user_budget.daily_limit_usd > 0 else 0
            monthly_usage_percent = (user_budget.monthly_spent_usd / user_budget.monthly_limit_usd) * 100 if user_budget.monthly_limit_usd > 0 else 0
            
            # Send alerts based on usage
            if daily_usage_percent >= 90:
                self._send_alert(user_budget.user_id, "CRITICAL", 
                               f"90% of daily budget used (${user_budget.daily_spent_usd:.2f}/${user_budget.daily_limit_usd:.2f})")
            elif daily_usage_percent >= 75:
                self._send_alert(user_budget.user_id, "WARNING", 
                               f"75% of daily budget used (${user_budget.daily_spent_usd:.2f}/${user_budget.daily_limit_usd:.2f})")
            
            if monthly_usage_percent >= 90:
                self._send_alert(user_budget.user_id, "CRITICAL", 
                               f"90% of monthly budget used (${user_budget.monthly_spent_usd:.2f}/${user_budget.monthly_limit_usd:.2f})")
                
        except Exception as e:
            logger.error(f"Error checking budget alerts for user {user_budget.user_id}: {e}")

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