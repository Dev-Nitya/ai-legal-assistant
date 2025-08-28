import React, { useState } from "react";
import {
  FiBarChart as BarChart3,
  FiPlay as Play,
  FiFileText as FileText,
  FiTrendingUp as TrendingUp,
  FiClock as Clock,
  FiTarget as Target,
} from "react-icons/fi";
import { motion } from "framer-motion";

const EvaluationDashboard: React.FC = () => {
  const [isRunningEvaluation, setIsRunningEvaluation] = useState(false);

  const handleRunEvaluation = async () => {
    setIsRunningEvaluation(true);
    // TODO: Implement actual evaluation API call
    setTimeout(() => {
      setIsRunningEvaluation(false);
    }, 3000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <BarChart3 className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              RAG Evaluation Dashboard
            </h1>
            <p className="text-gray-600">
              Test and analyze AI legal assistant performance
            </p>
          </div>
        </div>

        <button
          onClick={handleRunEvaluation}
          disabled={isRunningEvaluation}
          className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:bg-blue-400 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
        >
          {isRunningEvaluation ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
              <span>Running...</span>
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              <span>Run Evaluation</span>
            </>
          )}
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-lg shadow-sm border border-slate-200 p-6"
        >
          <div className="flex items-center space-x-3">
            <Target className="h-8 w-8 text-green-600" />
            <div>
              <p className="text-sm text-gray-600">Avg. Precision</p>
              <p className="text-2xl font-bold text-gray-900">0.87</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-lg shadow-sm border border-slate-200 p-6"
        >
          <div className="flex items-center space-x-3">
            <TrendingUp className="h-8 w-8 text-blue-600" />
            <div>
              <p className="text-sm text-gray-600">Faithfulness</p>
              <p className="text-2xl font-bold text-gray-900">0.92</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-white rounded-lg shadow-sm border border-slate-200 p-6"
        >
          <div className="flex items-center space-x-3">
            <FileText className="h-8 w-8 text-purple-600" />
            <div>
              <p className="text-sm text-gray-600">Tests Run</p>
              <p className="text-2xl font-bold text-gray-900">1,247</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-lg shadow-sm border border-slate-200 p-6"
        >
          <div className="flex items-center space-x-3">
            <Clock className="h-8 w-8 text-orange-600" />
            <div>
              <p className="text-sm text-gray-600">Avg. Response Time</p>
              <p className="text-2xl font-bold text-gray-900">2.3s</p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Evaluation Form */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Single Question Evaluation
        </h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Test Question
            </label>
            <textarea
              rows={3}
              placeholder="Enter a legal question to test..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Category
              </label>
              <select className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                <option value="">All Categories</option>
                <option value="constitutional">Constitutional Law</option>
                <option value="criminal">Criminal Law</option>
                <option value="civil">Civil Law</option>
                <option value="contract">Contract Law</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Difficulty
              </label>
              <select className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                <option value="">All Levels</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">
                Use ground truth
              </span>
            </label>
          </div>

          <button
            className="bg-green-600 text-white px-6 py-2 rounded-md hover:bg-green-700 transition-colors"
            disabled={isRunningEvaluation}
          >
            Evaluate Single Question
          </button>
        </div>
      </div>

      {/* Batch Evaluation */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Batch Evaluation
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Questions
            </label>
            <input
              type="number"
              min="1"
              max="100"
              defaultValue={10}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Category Filter
            </label>
            <select className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
              <option value="">All Categories</option>
              <option value="constitutional">Constitutional Law</option>
              <option value="criminal">Criminal Law</option>
              <option value="civil">Civil Law</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Difficulty Filter
            </label>
            <select className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent">
              <option value="">All Levels</option>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </div>
        </div>

        <button
          className="bg-purple-600 text-white px-6 py-2 rounded-md hover:bg-purple-700 transition-colors"
          disabled={isRunningEvaluation}
        >
          Run Batch Evaluation
        </button>
      </div>

      {/* Recent Results */}
      <div className="bg-white rounded-lg shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Recent Evaluation Results
        </h2>

        <div className="space-y-4">
          <div className="text-center text-gray-500 py-8">
            <BarChart3 className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>
              No evaluation results yet. Run an evaluation to see results here.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EvaluationDashboard;
