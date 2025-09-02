import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FiSettings as Settings,
  FiZap as Zap,
  FiChevronDown as ChevronDown,
  FiRotateCcw as RotateCcw,
  FiX as X,
} from "react-icons/fi";
import type { ComplexityLevel } from "../types";

interface ChatSettingsProps {
  complexity: ComplexityLevel;
  onComplexityChange: (complexity: ComplexityLevel) => void;
  onReset: () => void;
}

const ChatSettings: React.FC<ChatSettingsProps> = ({
  complexity,
  onComplexityChange,
  onReset,
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<"general" | "filters">("general");

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white/30 overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-gray-200/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Settings className="h-5 w-5 text-primary-600" />
            <h3 className="text-lg font-semibold text-gray-800">
              Chat Settings
            </h3>
          </div>
          <div className="flex items-center space-x-2">
            <motion.button
              onClick={onReset}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors duration-200"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              title="Reset to defaults"
            >
              <RotateCcw className="h-4 w-4" />
            </motion.button>
            <motion.button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors duration-200"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <motion.div
                animate={{ rotate: isExpanded ? 180 : 0 }}
                transition={{ duration: 0.2 }}
              >
                <ChevronDown className="h-4 w-4" />
              </motion.div>
            </motion.button>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            {/* Tabs */}
            <div className="flex border-b border-gray-200/50">
              <motion.button
                onClick={() => setActiveTab("general")}
                className={`flex-1 px-4 py-3 text-sm font-medium transition-colors duration-200 ${
                  activeTab === "general"
                    ? "text-primary-600 border-b-2 border-primary-500 bg-primary-50/50"
                    : "text-gray-600 hover:text-gray-800"
                }`}
                whileHover={{
                  backgroundColor:
                    activeTab === "general" ? undefined : "rgba(0,0,0,0.02)",
                }}
              >
                <div className="flex items-center justify-center space-x-2">
                  <Zap className="h-4 w-4" />
                  <span>General</span>
                </div>
              </motion.button>
            </div>

            <div className="p-6">
              {activeTab === "general" && (
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="space-y-6"
                >
                  {/* Complexity Level */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-3">
                      Response Complexity
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      {(
                        [
                          "simple",
                          "intermediate",
                          "advanced",
                        ] as ComplexityLevel[]
                      ).map((level) => (
                        <motion.button
                          key={level}
                          onClick={() => onComplexityChange(level)}
                          className={`p-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                            complexity === level
                              ? "bg-primary-500 text-white shadow-md"
                              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                          }`}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                        >
                          {level.charAt(0).toUpperCase() + level.slice(1)}
                        </motion.button>
                      ))}
                    </div>
                  </div>

                  {/* Toggle Settings */}
                </motion.div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default ChatSettings;
