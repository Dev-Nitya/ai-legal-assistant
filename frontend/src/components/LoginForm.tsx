import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  FiMail as Mail,
  FiLock as Lock,
  FiLogIn as LogIn,
  FiUserPlus as UserPlus,
  FiLoader as Loader2,
} from "react-icons/fi";
import { useAuth } from "../hooks/useAuth";
import type { AuthRequest, RegisterRequest, UserTier } from "../types";

interface LoginFormProps {
  onSuccess?: () => void;
}

const LoginForm: React.FC<LoginFormProps> = ({ onSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    full_name: "",
    tier: "free" as UserTier,
  });
  const { login, register, isLoading } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      if (isLogin) {
        const credentials: AuthRequest = {
          email: formData.email,
          password: formData.password,
        };
        await login(credentials);
      } else {
        const userData: RegisterRequest = {
          email: formData.email,
          password: formData.password,
          full_name: formData.full_name,
          tier: formData.tier,
        };
        await register(userData);
      }
      onSuccess?.();
    } catch (err) {
      // Error handling is now done in AuthContext with toast notifications
      console.error("Auth error:", err);
    }
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-md mx-auto bg-white/90 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/30 p-8"
    >
      <div className="text-center mb-8">
        <motion.div
          className="w-16 h-16 bg-gradient-to-r from-primary-500 to-primary-700 rounded-full flex items-center justify-center mx-auto mb-4"
          whileHover={{ scale: 1.05 }}
        >
          {isLogin ? (
            <LogIn className="h-8 w-8 text-white" />
          ) : (
            <UserPlus className="h-8 w-8 text-white" />
          )}
        </motion.div>
        <h2 className="text-2xl font-bold text-gray-800 mb-2">
          {isLogin ? "Welcome Back" : "Create Account"}
        </h2>
        <p className="text-gray-600">
          {isLogin
            ? "Sign in to access your AI Legal Assistant"
            : "Join the AI Legal Assistant platform"}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {!isLogin && (
          <div>
            <label
              htmlFor="full_name"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Full Name
            </label>
            <input
              type="text"
              id="full_name"
              name="full_name"
              value={formData.full_name}
              onChange={handleInputChange}
              required={!isLogin}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-400 focus:border-primary-400 transition-all duration-200 bg-white/80"
              placeholder="Enter your full name"
            />
          </div>
        )}

        <div>
          <label
            htmlFor="email"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Email Address
          </label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              required
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-400 focus:border-primary-400 transition-all duration-200 bg-white/80"
              placeholder="Enter your email"
            />
          </div>
        </div>

        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Password
          </label>
          <div className="relative">
            <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleInputChange}
              required
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-400 focus:border-primary-400 transition-all duration-200 bg-white/80"
              placeholder="Enter your password"
            />
          </div>
        </div>

        {!isLogin && (
          <div>
            <label
              htmlFor="tier"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Subscription Tier
            </label>
            <select
              id="tier"
              name="tier"
              value={formData.tier}
              onChange={handleInputChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-400 focus:border-primary-400 transition-all duration-200 bg-white/80"
            >
              <option value="free">Free Tier</option>
              <option value="basic">Basic Tier</option>
              <option value="premium">Premium Tier</option>
              <option value="enterprise">Enterprise Tier</option>
            </select>
          </div>
        )}

        <motion.button
          type="submit"
          disabled={isLoading}
          className="w-full py-3 px-4 bg-gradient-to-r from-primary-500 to-primary-700 text-white font-semibold rounded-xl shadow-lg hover:from-primary-600 hover:to-primary-800 focus:ring-2 focus:ring-primary-400 focus:ring-offset-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {isLoading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Processing...</span>
            </>
          ) : (
            <>
              {isLogin ? (
                <LogIn className="h-5 w-5" />
              ) : (
                <UserPlus className="h-5 w-5" />
              )}
              <span>{isLogin ? "Sign In" : "Create Account"}</span>
            </>
          )}
        </motion.button>
      </form>

      <div className="mt-6 text-center">
        <p className="text-gray-600">
          {isLogin ? "Don't have an account?" : "Already have an account?"}
        </p>
        <motion.button
          type="button"
          onClick={() => {
            setIsLogin(!isLogin);
            setFormData({
              email: "",
              password: "",
              full_name: "",
              tier: "free",
            });
          }}
          className="mt-2 text-primary-600 hover:text-primary-700 font-semibold transition-colors duration-200"
          whileHover={{ scale: 1.05 }}
        >
          {isLogin ? "Create an account" : "Sign in instead"}
        </motion.button>
      </div>
    </motion.div>
  );
};

export default LoginForm;
