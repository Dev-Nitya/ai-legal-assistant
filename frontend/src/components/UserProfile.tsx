import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FiX as X,
  FiUser as User,
  FiMail as Mail,
  FiCalendar as Calendar,
  FiAward as Crown,
  FiLogOut as LogOut,
  FiDollarSign as DollarSign,
} from "react-icons/fi";
import type { User as UserType } from "../types";

interface UserProfileProps {
  isOpen: boolean;
  onClose: () => void;
  user: UserType | null;
  onLogout: () => void;
}

const UserProfile: React.FC<UserProfileProps> = ({
  isOpen,
  onClose,
  user,
  onLogout,
}) => {
  if (!isOpen || !user) return null;

  const handleLogout = () => {
    onLogout();
    onClose();
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case "free":
        return "bg-gray-100 text-gray-700";
      case "basic":
        return "bg-blue-100 text-blue-700";
      case "premium":
        return "bg-purple-100 text-purple-700";
      case "enterprise":
        return "bg-gold-100 text-yellow-700";
      default:
        return "bg-gray-100 text-gray-700";
    }
  };

  const getTierIcon = () => {
    if (user.tier === "premium" || user.tier === "enterprise") {
      return <Crown className="h-4 w-4" />;
    }
    return <User className="h-4 w-4" />;
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black bg-opacity-50"
          onClick={onClose}
        />

        {/* Modal */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative bg-white rounded-lg shadow-xl w-full max-w-md mx-4"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <User className="h-6 w-6 text-blue-600" />
              <h2 className="text-xl font-semibold text-gray-900">Profile</h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* User Info */}
            <div className="text-center">
              <div className="mx-auto w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                <User className="h-10 w-10 text-blue-600" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900">
                {user.full_name}
              </h3>
              <p className="text-gray-600">{user.email}</p>
            </div>

            {/* Account Details */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Mail className="h-5 w-5 text-gray-400" />
                  <span className="text-sm text-gray-600">Email</span>
                </div>
                <span className="text-sm font-medium text-gray-900">
                  {user.email}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  {getTierIcon()}
                  <span className="text-sm text-gray-600">Tier</span>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${getTierColor(
                    user.tier
                  )}`}
                >
                  {user.tier}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <Calendar className="h-5 w-5 text-gray-400" />
                  <span className="text-sm text-gray-600">Member Since</span>
                </div>
                <span className="text-sm font-medium text-gray-900">
                  {user.created_at
                    ? new Date(user.created_at).toLocaleDateString()
                    : "N/A"}
                </span>
              </div>
            </div>

            {/* Budget Info */}
            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
              <div className="flex items-center space-x-2 mb-2">
                <DollarSign className="h-5 w-5 text-green-600" />
                <span className="font-medium text-gray-900">Budget Usage</span>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Daily Limit</span>
                  <span className="font-medium">
                    $
                    {user.budget_info?.limits.daily_limit_usd.toFixed(2) ||
                      "0.00"}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Daily Spent</span>
                  <span className="font-medium text-red-600">
                    $
                    {user.budget_info?.usage.daily_spent_usd.toFixed(2) ||
                      "0.00"}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.min(
                        ((user.budget_info?.usage.daily_spent_usd || 0) /
                          (user.budget_info?.limits.daily_limit_usd || 1)) *
                          100,
                        100
                      )}%`,
                    }}
                  ></div>
                </div>
              </div>

              <div className="space-y-2 pt-2 border-t border-gray-200">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Monthly Limit</span>
                  <span className="font-medium">
                    $
                    {user.budget_info?.limits.monthly_limit_usd.toFixed(2) ||
                      "0.00"}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Monthly Spent</span>
                  <span className="font-medium text-red-600">
                    $
                    {user.budget_info?.usage.monthly_spent_usd.toFixed(2) ||
                      "0.00"}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-green-600 h-2 rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.min(
                        ((user.budget_info?.usage.monthly_spent_usd || 0) /
                          (user.budget_info?.limits.monthly_limit_usd || 1)) *
                          100,
                        100
                      )}%`,
                    }}
                  ></div>
                </div>
              </div>

              <div className="flex justify-between text-sm pt-2">
                <span className="text-gray-600">Requests This Hour</span>
                <span className="font-medium">
                  {user.budget_info?.usage.hourly_spent || 0}
                </span>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-lg">
            <button
              onClick={handleLogout}
              className="w-full bg-red-600 text-white py-2 px-4 rounded-md hover:bg-red-700 transition-colors flex items-center justify-center space-x-2"
            >
              <LogOut className="h-4 w-4" />
              <span>Sign Out</span>
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default UserProfile;
