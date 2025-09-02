import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  FiPlay as Play,
  FiBarChart as BarChart3,
  FiTarget as Target,
  FiClock as Clock,
  FiCheckCircle as CheckCircle,
  FiAlertCircle as AlertCircle,
  FiDownload as Download,
  FiLoader as Loader2,
  FiFileText as FileText,
  FiTrendingUp as TrendingUp,
} from "react-icons/fi";
import type {
  EvaluationRequest,
  BatchEvaluationRequest,
  EvaluationResponse,
  BatchEvaluationResponse,
  User,
} from "../types";

interface EvaluationInterfaceProps {
  token?: string;
  user?: User;
}

const EvaluationInterface: React.FC<EvaluationInterfaceProps> = ({
  token,
  user,
}) => {
  const [activeTab, setActiveTab] = useState<"single" | "batch">("single");
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<
    EvaluationResponse | BatchEvaluationResponse | null
  >(null);
  const [error, setError] = useState<string | null>(null);

  // Single evaluation state
  const [singleQuestion, setSingleQuestion] = useState("");
  const [useGroundTruth, setUseGroundTruth] = useState(false);
  const [groundTruthAnswer, setGroundTruthAnswer] = useState("");

  // Batch evaluation state
  const [batchConfig, setBatchConfig] = useState<BatchEvaluationRequest>({
    category: "",
    difficulty: "",
    max_questions: 5,
    user_id: user?.user_id || "anonymous",
  });

  const API_BASE_URL = "http://localhost:8000/api";

  // Update batch config user_id when user changes
  useEffect(() => {
    setBatchConfig((prev) => ({
      ...prev,
      user_id: user?.user_id || "anonymous",
    }));
  }, [user?.user_id]);

  const runSingleEvaluation = async () => {
    if (!singleQuestion.trim()) return;

    setIsLoading(true);
    setError(null);
    setResults(null);

    try {
      const request: EvaluationRequest = {
        question: singleQuestion,
        user_id: user?.user_id || "anonymous",
        use_ground_truth: useGroundTruth,
        ground_truth_answer: useGroundTruth ? groundTruthAnswer : undefined,
      };

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };

      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/evaluate/single`, {
        method: "POST",
        headers,
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Evaluation failed");
      }

      const data: EvaluationResponse = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  const runBatchEvaluation = async () => {
    setIsLoading(true);
    setError(null);
    setResults(null);

    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };

      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE_URL}/evaluate/batch`, {
        method: "POST",
        headers,
        body: JSON.stringify(batchConfig),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Batch evaluation failed");
      }

      const data: BatchEvaluationResponse = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  const formatScore = (score: number) => {
    return (score * 100).toFixed(1) + "%";
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "text-green-600";
    if (score >= 0.6) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white/30 p-6"
    >
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 mb-2 flex items-center space-x-2">
          <BarChart3 className="h-6 w-6 text-primary-600" />
          <span>RAG System Evaluation</span>
        </h2>
        <p className="text-gray-600">
          Test and evaluate the performance of your legal AI assistant
        </p>
      </div>

      {/* Tabs */}
      <div className="flex mb-6 bg-gray-100 rounded-xl p-1">
        <motion.button
          onClick={() => setActiveTab("single")}
          className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all duration-200 ${
            activeTab === "single"
              ? "bg-white text-primary-600 shadow-sm"
              : "text-gray-600 hover:text-gray-800"
          }`}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <div className="flex items-center justify-center space-x-2">
            <Target className="h-4 w-4" />
            <span>Single Question</span>
          </div>
        </motion.button>
        <motion.button
          onClick={() => setActiveTab("batch")}
          className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-all duration-200 ${
            activeTab === "batch"
              ? "bg-white text-primary-600 shadow-sm"
              : "text-gray-600 hover:text-gray-800"
          }`}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          <div className="flex items-center justify-center space-x-2">
            <FileText className="h-4 w-4" />
            <span>Batch Evaluation</span>
          </div>
        </motion.button>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center space-x-3 text-red-700"
        >
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <span className="text-sm font-medium">{error}</span>
        </motion.div>
      )}

      {/* Single Question Tab */}
      {activeTab === "single" && (
        <div className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Legal Question
            </label>
            <textarea
              value={singleQuestion}
              onChange={(e) => setSingleQuestion(e.target.value)}
              placeholder="Enter a legal question to evaluate..."
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-400 focus:border-primary-400 transition-all duration-200 resize-none h-24"
            />
          </div>

          <div className="flex items-center space-x-3">
            <input
              type="checkbox"
              id="useGroundTruth"
              checked={useGroundTruth}
              onChange={(e) => setUseGroundTruth(e.target.checked)}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
            <label
              htmlFor="useGroundTruth"
              className="text-sm font-medium text-gray-700"
            >
              Use ground truth answer for comparison
            </label>
          </div>

          {useGroundTruth && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
            >
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Ground Truth Answer
              </label>
              <textarea
                value={groundTruthAnswer}
                onChange={(e) => setGroundTruthAnswer(e.target.value)}
                placeholder="Enter the expected correct answer..."
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-400 focus:border-primary-400 transition-all duration-200 resize-none h-24"
              />
            </motion.div>
          )}

          <motion.button
            onClick={runSingleEvaluation}
            disabled={isLoading || !singleQuestion.trim()}
            className="w-full py-3 px-4 bg-gradient-to-r from-primary-500 to-primary-700 text-white font-semibold rounded-xl shadow-lg hover:from-primary-600 hover:to-primary-800 focus:ring-2 focus:ring-primary-400 focus:ring-offset-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Evaluating...</span>
              </>
            ) : (
              <>
                <Play className="h-5 w-5" />
                <span>Run Evaluation</span>
              </>
            )}
          </motion.button>
        </div>
      )}

      {/* Batch Evaluation Tab */}
      {activeTab === "batch" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Category Filter
              </label>
              <select
                value={batchConfig.category || ""}
                onChange={(e) =>
                  setBatchConfig((prev) => ({
                    ...prev,
                    category: e.target.value || undefined,
                  }))
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">All Categories</option>
                <option value="criminal_law">Criminal Law</option>
                <option value="civil_law">Civil Law</option>
                <option value="constitutional_law">Constitutional Law</option>
                <option value="corporate_law">Corporate Law</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Difficulty Level
              </label>
              <select
                value={batchConfig.difficulty || ""}
                onChange={(e) =>
                  setBatchConfig((prev) => ({
                    ...prev,
                    difficulty: e.target.value || undefined,
                  }))
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">All Difficulties</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Maximum Questions: {batchConfig.max_questions}
            </label>
            <input
              type="range"
              min="1"
              max="20"
              value={batchConfig.max_questions}
              onChange={(e) =>
                setBatchConfig((prev) => ({
                  ...prev,
                  max_questions: parseInt(e.target.value),
                }))
              }
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>1</span>
              <span>10</span>
              <span>20</span>
            </div>
          </div>

          <motion.button
            onClick={runBatchEvaluation}
            disabled={isLoading}
            className="w-full py-3 px-4 bg-gradient-to-r from-primary-500 to-primary-700 text-white font-semibold rounded-xl shadow-lg hover:from-primary-600 hover:to-primary-800 focus:ring-2 focus:ring-primary-400 focus:ring-offset-2 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                <span>Running Batch Evaluation...</span>
              </>
            ) : (
              <>
                <Play className="h-5 w-5" />
                <span>Run Batch Evaluation</span>
              </>
            )}
          </motion.button>
        </div>
      )}

      {/* Results Section */}
      {results && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-8 space-y-6"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-semibold text-gray-800">
              Evaluation Results
            </h3>
          </div>

          {/* Single Evaluation Results */}
          {"question" in results && (
            <div className="space-y-4">
              <div className="bg-gray-50 p-4 rounded-xl">
                <h4 className="font-medium text-gray-800 mb-2">Question:</h4>
                <p className="text-gray-700">{results.question}</p>
              </div>

              <div className="bg-gray-50 p-4 rounded-xl">
                <h4 className="font-medium text-gray-800 mb-2">
                  Generated Answer:
                </h4>
                <p className="text-gray-700">{results.generated_answer}</p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(results.evaluation_result).map(
                  ([key, value]) => (
                    <div
                      key={key}
                      className="bg-white p-4 rounded-xl border border-gray-200"
                    >
                      <div className="flex items-center space-x-2 mb-2">
                        <TrendingUp className="h-4 w-4 text-primary-500" />
                        <span className="text-sm font-medium text-gray-600 capitalize">
                          {key.replace(/_/g, " ")}
                        </span>
                      </div>
                      <p
                        className={`text-lg font-bold ${getScoreColor(
                          typeof value === "number" ? value : 0
                        )}`}
                      >
                        {typeof value === "number" ? formatScore(value) : value}
                      </p>
                    </div>
                  )
                )}
              </div>

              <div className="flex items-center justify-between text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
                <div className="flex items-center space-x-2">
                  <Clock className="h-4 w-4" />
                  <span>
                    Processing Time:{" "}
                    {results.processing_time_seconds.toFixed(2)}s
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <FileText className="h-4 w-4" />
                  <span>
                    Documents Retrieved: {results.retrieved_documents_count}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Batch Evaluation Results */}
          {"total_questions_tested" in results && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white p-6 rounded-xl border border-gray-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">
                        Questions Tested
                      </p>
                      <p className="text-2xl font-bold text-gray-800">
                        {results.total_questions_tested}
                      </p>
                    </div>
                    <CheckCircle className="h-8 w-8 text-green-500" />
                  </div>
                </div>

                <div className="bg-white p-6 rounded-xl border border-gray-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">
                        Average Score
                      </p>
                      <p className="text-2xl font-bold text-primary-600">
                        {formatScore(results.average_scores.overall_score || 0)}
                      </p>
                    </div>
                    <TrendingUp className="h-8 w-8 text-primary-500" />
                  </div>
                </div>

                <div className="bg-white p-6 rounded-xl border border-gray-200">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">
                        Categories
                      </p>
                      <p className="text-2xl font-bold text-gray-800">
                        {Object.keys(results.category_breakdown).length}
                      </p>
                    </div>
                    <BarChart3 className="h-8 w-8 text-blue-500" />
                  </div>
                </div>
              </div>

              <div className="bg-white p-6 rounded-xl border border-gray-200">
                <h4 className="font-semibold text-gray-800 mb-4">
                  Average Scores by Metric
                </h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {Object.entries(results.average_scores).map(
                    ([metric, score]) => (
                      <div key={metric} className="text-center">
                        <p className="text-sm text-gray-600 capitalize mb-1">
                          {metric.replace(/_/g, " ")}
                        </p>
                        <p
                          className={`text-lg font-bold ${getScoreColor(
                            score
                          )}`}
                        >
                          {formatScore(score)}
                        </p>
                      </div>
                    )
                  )}
                </div>
              </div>

              {Object.keys(results.category_breakdown).length > 0 && (
                <div className="bg-white p-6 rounded-xl border border-gray-200">
                  <h4 className="font-semibold text-gray-800 mb-4">
                    Performance by Category
                  </h4>
                  <div className="space-y-3">
                    {Object.entries(results.category_breakdown).map(
                      ([category, scores]) => (
                        <div
                          key={category}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                        >
                          <span className="font-medium text-gray-700 capitalize">
                            {category}
                          </span>
                          <div className="flex space-x-4 text-sm">
                            {Object.entries(scores).map(([metric, score]) => (
                              <span
                                key={metric}
                                className={`font-medium ${getScoreColor(
                                  score
                                )}`}
                              >
                                {metric}: {formatScore(score)}
                              </span>
                            ))}
                          </div>
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </motion.div>
      )}
    </motion.div>
  );
};

export default EvaluationInterface;
