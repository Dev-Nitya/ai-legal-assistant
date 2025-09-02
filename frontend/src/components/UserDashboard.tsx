import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  FiUser as User,
  FiAward as Crown,
  FiDollarSign as DollarSign,
  FiCalendar as Calendar,
  FiLogOut as LogOut,
  FiSettings as Settings,
  FiActivity as Activity,
  FiTrendingUp as TrendingUp,
  FiShield as Shield,
  FiRefreshCw as RefreshCw,
} from "react-icons/fi";
import { useAuth } from "../hooks/useAuth";
import { useBudgetRefresh } from "../hooks/useBudgetRefresh";

const UserDashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const { refreshBudget } = useBudgetRefresh();
  const [isExpanded, setIsExpanded] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await refreshBudget();
    } finally {
      setIsRefreshing(false);
    }
  };

  if (!user) {
    return null;
  }

  const getTierIcon = (tier: string) => {
    switch (tier) {
      case "enterprise":
        return <Crown className="h-5 w-5 text-purple-500" />;
      case "premium":
        return <Crown className="h-5 w-5 text-amber-500" />;
      case "basic":
        return <Shield className="h-5 w-5 text-blue-500" />;
      default:
        return <User className="h-5 w-5 text-gray-500" />;
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case "enterprise":
        return "from-purple-500 to-purple-700";
      case "premium":
        return "from-amber-500 to-amber-700";
      case "basic":
        return "from-blue-500 to-blue-700";
      default:
        return "from-gray-500 to-gray-700";
    }
  };

  const formatCurrency = (amount: number, digits: number = 2) => {
    if (amount == null || Number.isNaN(amount)) return "—";

    const maxDigits = 8;
    let currentDigits = Math.max(0, digits);

    for (; currentDigits <= maxDigits; currentDigits++) {
      const mul = Math.pow(10, currentDigits);
      const truncated = Math.trunc(amount * mul) / mul;

      // If truncated is non-zero (or we've reached max precision) format and return
      if (truncated !== 0 || currentDigits === maxDigits) {
        return new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "USD",
          minimumFractionDigits: currentDigits,
          maximumFractionDigits: currentDigits,
        }).format(truncated);
      }
      // otherwise increment digits and try again
    }

    // fallback (shouldn't reach)
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(0);
  };

  const calculateUsagePercentage = (used: number, limit: number) => {
    return Math.min((used / limit) * 100, 100);
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white/30 overflow-hidden"
    >
      {/* Header */}
      <div className={`bg-gradient-to-r ${getTierColor(user.tier)} p-6`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-white/20 backdrop-blur-md rounded-full flex items-center justify-center">
              <User className="h-6 w-6 text-white" />
            </div>
            <div>
              <h3 className="text-white font-semibold text-lg">
                {user.full_name}
              </h3>
              <div className="flex items-center space-x-2">
                {getTierIcon(user.tier)}
                <span className="text-white/90 text-sm capitalize font-medium">
                  {user.tier} Plan
                </span>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <motion.button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="text-white/80 hover:text-white transition-colors duration-200 disabled:opacity-50"
              whileHover={!isRefreshing ? { scale: 1.1 } : {}}
              whileTap={!isRefreshing ? { scale: 0.9 } : {}}
              title="Refresh budget data"
            >
              <RefreshCw
                className={`h-5 w-5 ${isRefreshing ? "animate-spin" : ""}`}
              />
            </motion.button>
            <motion.button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-white/80 hover:text-white transition-colors duration-200"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
            >
              <Settings className="h-5 w-5" />
            </motion.button>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="p-6">
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-gradient-to-br from-green-50 to-green-100 p-4 rounded-xl border border-green-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-green-600 text-sm font-medium">Status</p>
                <p className="text-green-800 font-semibold">
                  {user.is_active ? "Active" : "Inactive"}
                </p>
              </div>
              <Activity className="h-8 w-8 text-green-500" />
            </div>
          </div>

          <div className="bg-gradient-to-br from-blue-50 to-blue-100 p-4 rounded-xl border border-blue-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-600 text-sm font-medium">
                  Member Since
                </p>
                <p className="text-blue-800 font-semibold text-sm">
                  {user.created_at
                    ? new Date(user.created_at).toLocaleDateString()
                    : "N/A"}
                </p>
              </div>
              <Calendar className="h-8 w-8 text-blue-500" />
            </div>
          </div>
        </div>

        {/* Budget Information */}
        {(user.budget_info || user.budget_limits) && (
          <div className="space-y-4">
            <h4 className="text-gray-800 font-semibold flex items-center space-x-2">
              <DollarSign className="h-5 w-5 text-green-500" />
              <span>Budget Overview</span>
            </h4>

            {user.budget_info ? (
              <div className="space-y-3">
                {/* Daily Budget */}
                <div className="bg-gray-50 p-4 rounded-xl">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-700 font-medium">
                      Daily Budget
                    </span>
                    <span className="text-gray-600 text-sm">
                      {formatCurrency(
                        Math.max(
                          0,
                          user.budget_info.limits.daily_limit -
                            user.budget_info.usage.daily_spent
                        )
                      )}{" "}
                      / {formatCurrency(user.budget_info.limits.daily_limit)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <motion.div
                      className={`h-2 rounded-full ${
                        calculateUsagePercentage(
                          user.budget_info.usage.daily_spent,
                          user.budget_info.limits.daily_limit
                        ) > 80
                          ? "bg-gradient-to-r from-red-400 to-red-600"
                          : calculateUsagePercentage(
                              user.budget_info.usage.daily_spent,
                              user.budget_info.limits.daily_limit
                            ) > 60
                          ? "bg-gradient-to-r from-yellow-400 to-yellow-600"
                          : "bg-gradient-to-r from-green-400 to-green-600"
                      }`}
                      initial={{ width: 0 }}
                      animate={{
                        width: `${calculateUsagePercentage(
                          user.budget_info.usage.daily_spent,
                          user.budget_info.limits.daily_limit
                        )}%`,
                      }}
                      transition={{ duration: 1, ease: "easeOut" }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Spent:{" "}
                    {formatCurrency(user.budget_info.usage.daily_spent, 4)} (
                    {calculateUsagePercentage(
                      user.budget_info.usage.daily_spent,
                      user.budget_info.limits.daily_limit
                    ).toFixed(3)}
                    %)
                  </p>
                </div>

                {/* Monthly Budget */}
                <div className="bg-gray-50 p-4 rounded-xl">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-gray-700 font-medium">
                      Monthly Budget
                    </span>
                    <span className="text-gray-600 text-sm">
                      {formatCurrency(
                        Math.max(
                          0,
                          user.budget_info.limits.monthly_limit -
                            user.budget_info.usage.monthly_spent
                        )
                      )}{" "}
                      / {formatCurrency(user.budget_info.limits.monthly_limit)}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <motion.div
                      className={`h-2 rounded-full ${
                        calculateUsagePercentage(
                          user.budget_info.usage.monthly_spent,
                          user.budget_info.limits.monthly_limit
                        ) > 80
                          ? "bg-gradient-to-r from-red-400 to-red-600"
                          : calculateUsagePercentage(
                              user.budget_info.usage.monthly_spent,
                              user.budget_info.limits.monthly_limit
                            ) > 60
                          ? "bg-gradient-to-r from-yellow-400 to-yellow-600"
                          : "bg-gradient-to-r from-blue-400 to-blue-600"
                      }`}
                      initial={{ width: 0 }}
                      animate={{
                        width: `${calculateUsagePercentage(
                          user.budget_info.usage.monthly_spent,
                          user.budget_info.limits.monthly_limit
                        )}%`,
                      }}
                      transition={{ duration: 1, delay: 0.2, ease: "easeOut" }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Spent:{" "}
                    {formatCurrency(user.budget_info.usage.monthly_spent, 4)} (
                    {calculateUsagePercentage(
                      user.budget_info.usage.monthly_spent,
                      user.budget_info.limits.monthly_limit
                    ).toFixed(3)}
                    %)
                  </p>
                </div>
              </div>
            ) : (
              user.budget_limits && (
                <div className="bg-gray-50 p-4 rounded-xl">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Daily Limit:</span>
                      <p className="font-semibold text-gray-800">
                        {formatCurrency(user.budget_limits.daily || 0)}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-600">Weekly Limit:</span>
                      <p className="font-semibold text-gray-800">
                        {formatCurrency(user.budget_limits.weekly || 0)}
                      </p>
                    </div>
                    <div>
                      <span className="text-gray-600">Monthly Limit:</span>
                      <p className="font-semibold text-gray-800">
                        {formatCurrency(user.budget_limits.monthly || 0)}
                      </p>
                    </div>
                  </div>
                </div>
              )
            )}
          </div>
        )}

        {/* Expanded Actions */}
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-6 pt-6 border-t border-gray-200"
          >
            <div className="space-y-3">
              <motion.button
                onClick={logout}
                className="w-full flex items-center space-x-3 p-3 text-red-600 hover:bg-red-50 rounded-xl transition-colors duration-200"
                whileHover={{ x: 5 }}
              >
                <LogOut className="h-5 w-5" />
                <span>Sign Out</span>
              </motion.button>
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
};

export default UserDashboard;
