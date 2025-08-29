import React from "react";
import {
  FiDollarSign as DollarSign,
  FiTrendingUp as TrendingUp,
  FiAlertTriangle as AlertTriangle,
} from "react-icons/fi";
import type { User } from "../types";

interface BudgetTrackerProps {
  user: User;
}

const BudgetTracker: React.FC<BudgetTrackerProps> = ({ user }) => {
  const { budget_info, budget_limits } = user;

  // Handle both budget_limits (from login) and budget_info (from profile) structures
  let dailyLimit, monthlyLimit, dailySpent, monthlySpent;

  if (budget_limits) {
    // Use budget_limits structure (from login/register response)
    dailyLimit = budget_limits.daily || 0;
    monthlyLimit = budget_limits.monthly || 0;
    // For limits-only structure, assume no spending info available
    dailySpent = 0;
    monthlySpent = 0;
  } else if (budget_info) {
    // Use nested budget_info structure (from profile endpoint)
    dailyLimit = budget_info.limits?.daily_limit || 0;
    monthlyLimit = budget_info.limits?.monthly_limit || 0;
    dailySpent = budget_info.usage?.daily_spent || 0;
    monthlySpent = budget_info.usage?.monthly_spent || 0;
  } else {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-yellow-700">Budget information not available</p>
      </div>
    );
  }

  const dailyPercentage = dailyLimit > 0 ? (dailySpent / dailyLimit) * 100 : 0;
  const monthlyPercentage =
    monthlyLimit > 0 ? (monthlySpent / monthlyLimit) * 100 : 0;

  const getDailyColor = () => {
    if (dailyPercentage >= 90) return "text-red-600";
    if (dailyPercentage >= 70) return "text-yellow-600";
    return "text-green-600";
  };

  const getMonthlyColor = () => {
    if (monthlyPercentage >= 90) return "text-red-600";
    if (monthlyPercentage >= 70) return "text-yellow-600";
    return "text-green-600";
  };

  return (
    <div className="flex items-center space-x-4 text-sm">
      {/* Daily Budget */}
      <div className="flex items-center space-x-2">
        <DollarSign className={`h-4 w-4 ${getDailyColor()}`} />
        <div className="text-gray-600">
          <span className="font-medium">Daily:</span>
          <span className={`ml-1 ${getDailyColor()}`}>
            ${dailySpent.toFixed(2)}/${dailyLimit.toFixed(2)}
          </span>
        </div>
        {dailyPercentage >= 90 && (
          <AlertTriangle className="h-4 w-4 text-red-500" />
        )}
      </div>

      {/* Monthly Budget */}
      <div className="flex items-center space-x-2">
        <TrendingUp className={`h-4 w-4 ${getMonthlyColor()}`} />
        <div className="text-gray-600">
          <span className="font-medium">Monthly:</span>
          <span className={`ml-1 ${getMonthlyColor()}`}>
            ${monthlySpent.toFixed(2)}/${monthlyLimit.toFixed(2)}
          </span>
        </div>
        {monthlyPercentage >= 90 && (
          <AlertTriangle className="h-4 w-4 text-red-500" />
        )}
      </div>

      {/* Tier Badge */}
      <div className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium capitalize">
        {user.tier}
      </div>
    </div>
  );
};

export default BudgetTracker;
