import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FiX as X,
  FiMail as Mail,
  FiLock as Lock,
  FiUser as User,
  FiEye as Eye,
  FiEyeOff as EyeOff,
} from "react-icons/fi";
import toast from "react-hot-toast";
import type { AuthRequest, RegisterRequest, UserTier } from "../types";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLogin: (credentials: AuthRequest) => Promise<void>;
  onRegister: (userData: RegisterRequest) => Promise<void>;
}

const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  onLogin,
  onRegister,
}) => {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const [loginForm, setLoginForm] = useState<AuthRequest>({
    email: "",
    password: "",
  });

  const [registerForm, setRegisterForm] = useState<RegisterRequest>({
    full_name: "",
    email: "",
    password: "",
    tier: "free" as UserTier,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (mode === "login") {
        await onLogin(loginForm);
        toast.success("Login successful!");
      } else {
        await onRegister(registerForm);
        toast.success("Registration successful!");
      }
      onClose();
      resetForms();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "An error occurred";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const resetForms = () => {
    setLoginForm({ email: "", password: "" });
    setRegisterForm({
      full_name: "",
      email: "",
      password: "",
      tier: "free" as UserTier,
    });
    setShowPassword(false);
  };

  const handleClose = () => {
    onClose();
    resetForms();
  };

  const switchMode = () => {
    setMode(mode === "login" ? "register" : "login");
    resetForms();
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="absolute inset-0 bg-black bg-opacity-50"
          onClick={handleClose}
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
            <h2 className="text-xl font-semibold text-gray-900">
              {mode === "login" ? "Sign In" : "Create Account"}
            </h2>
            <button
              onClick={handleClose}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Form */}
          <div className="p-6">
            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === "register" && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Full Name
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                    <input
                      type="text"
                      value={registerForm.full_name}
                      onChange={(e) =>
                        setRegisterForm((prev) => ({
                          ...prev,
                          full_name: e.target.value,
                        }))
                      }
                      className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter your full name"
                      required
                    />
                  </div>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    type="email"
                    value={
                      mode === "login" ? loginForm.email : registerForm.email
                    }
                    onChange={(e) => {
                      if (mode === "login") {
                        setLoginForm((prev) => ({
                          ...prev,
                          email: e.target.value,
                        }));
                      } else {
                        setRegisterForm((prev) => ({
                          ...prev,
                          email: e.target.value,
                        }));
                      }
                    }}
                    className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Enter your email"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    type={showPassword ? "text" : "password"}
                    value={
                      mode === "login"
                        ? loginForm.password
                        : registerForm.password
                    }
                    onChange={(e) => {
                      if (mode === "login") {
                        setLoginForm((prev) => ({
                          ...prev,
                          password: e.target.value,
                        }));
                      } else {
                        setRegisterForm((prev) => ({
                          ...prev,
                          password: e.target.value,
                        }));
                      }
                    }}
                    className="w-full pl-10 pr-12 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Enter your password"
                    required
                    minLength={6}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? (
                      <EyeOff className="h-5 w-5" />
                    ) : (
                      <Eye className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>

              {mode === "register" && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Account Tier
                  </label>
                  <select
                    value={registerForm.tier}
                    onChange={(e) =>
                      setRegisterForm((prev) => ({
                        ...prev,
                        tier: e.target.value as UserTier,
                      }))
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="free">Free</option>
                    <option value="basic">Basic</option>
                    <option value="premium">Premium</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                  <p className="text-sm text-gray-500 mt-1">
                    Free tier includes 10 queries per day
                  </p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
              >
                {loading ? (
                  <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
                ) : mode === "login" ? (
                  "Sign In"
                ) : (
                  "Create Account"
                )}
              </button>
            </form>

            <div className="mt-6 text-center">
              <p className="text-sm text-gray-600">
                {mode === "login"
                  ? "Don't have an account?"
                  : "Already have an account?"}{" "}
                <button
                  onClick={switchMode}
                  className="text-blue-600 hover:text-blue-700 font-medium"
                >
                  {mode === "login" ? "Sign up" : "Sign in"}
                </button>
              </p>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default AuthModal;
