import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FiBarChart as BarChart,
  FiTrendingUp as TrendingUp,
  FiTrendingDown as TrendingDown,
  FiRefreshCw as RefreshCw,
  FiClock as Clock,
  FiCheckCircle as CheckCircle,
  FiAlertCircle as AlertCircle,
  FiLoader as Loader,
  FiSearch as Search,
  FiEye as Eye,
  FiGitBranch as GitCompare,
  FiX as X,
  FiTrash2 as Trash2,
  FiPlay as Play,
  FiTarget as Target,
  FiActivity as Activity,
  FiAward as Award,
} from "react-icons/fi";

interface EvalRun {
  name: string;
  ts: number;
}

interface EvalRecord {
  name: string;
  metrics: Record<string, number>;
  samples: any[];
  meta: Record<string, any>;
  ts: number;
}

interface ComparisonResult {
  diffs: Record<
    string,
    {
      base: number;
      exp: number;
      delta: number;
      pct_change: number;
    }
  >;
  base_meta: Record<string, any>;
  exp_meta: Record<string, any>;
  exp_samples: any[];
}

interface EvaluationDashboardProps {
  token?: string;
}

const EvaluationDashboard: React.FC<EvaluationDashboardProps> = ({ token }) => {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<EvalRecord | null>(null);
  const [comparison, setComparison] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [compareMode, setCompareMode] = useState(false);
  const [selectedForComparison, setSelectedForComparison] = useState<string[]>(
    []
  );
  const [activeView, setActiveView] = useState<
    "overview" | "details" | "compare" | "run"
  >("overview");
  const [showRunForm, setShowRunForm] = useState(false);
  const [runForm, setRunForm] = useState({
    name: "",
    limit: 100,
    created_by: "",
    question_type: "easy",
  });
  const [isRunning, setIsRunning] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [runToDelete, setRunToDelete] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch("http://localhost:8000/api/eval/list", {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) throw new Error("Failed to fetch evaluation runs");
      const data = await response.json();
      setRuns(data.runs || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  const fetchRunDetails = async (name: string) => {
    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/eval/report?name=${encodeURIComponent(
          name
        )}`,
        {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }
      );
      if (!response.ok) throw new Error("Failed to fetch run details");
      const data = await response.json();
      setSelectedRun(data);
      setActiveView("details");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const compareRuns = async (base: string, exp: string) => {
    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/eval/compare?base=${encodeURIComponent(
          base
        )}&exp=${encodeURIComponent(exp)}`,
        {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }
      );
      if (!response.ok) throw new Error("Failed to compare runs");
      const data = await response.json();
      setComparison(data);
      setActiveView("compare");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const runAndStoreEvaluation = async (
    name: string,
    limit: number,
    created_by?: string,
    question_type: string = "easy"
  ) => {
    setIsRunning(true);
    setError(null);
    try {
      // Extract user_id from token if available
      let user_id: string | undefined;
      if (token) {
        try {
          const payload = JSON.parse(atob(token.split(".")[1]));
          user_id = payload.sub || payload.user_id || payload.id;
        } catch (err) {
          console.warn("Failed to parse user_id from token:", err);
        }
      }

      const response = await fetch(
        `http://localhost:8000/api/eval/run_and_store`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify({
            name,
            limit,
            created_by,
            user_id,
            question_type,
          }),
        }
      );

      if (!response.ok) throw new Error("Failed to run and store evaluation");
      const data = await response.json();

      // Refresh the runs list after successful execution
      await fetchRuns();

      // Reset form and close modal
      setRunForm({
        name: "",
        limit: 100,
        created_by: "",
        question_type: "easy",
      });
      setShowRunForm(false);

      return data;
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setIsRunning(false);
    }
  };

  const deleteRun = async (runName: string) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/eval/name/${encodeURIComponent(runName)}`,
        {
          method: "DELETE",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }
      );

      if (!response.ok) throw new Error("Failed to delete evaluation run");

      // Refresh the runs list after successful deletion
      await fetchRuns();

      // If the deleted run was currently selected, clear the selection
      if (selectedRun && selectedRun.name === runName) {
        setSelectedRun(null);
        setActiveView("overview");
      }
    } catch (err: any) {
      setError(err.message);
      throw err;
    }
  };

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  const filteredRuns = runs.filter((run) =>
    run.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatTimestamp = (ts: number) => {
    return new Date(ts).toLocaleString();
  };

  const formatMetricValue = (value: number, key: string) => {
    // Ensure value is a number
    if (typeof value !== "number" || isNaN(value)) {
      return String(value);
    }

    // Format latency metrics (including the new p50 and p95 fields)
    if (key.includes("time") || key.includes("latency")) {
      return `${value.toFixed(2)}ms`;
    }

    // Format percentage-based metrics
    if (
      key.includes("score") ||
      key.includes("accuracy") ||
      key.includes("precision") ||
      key.includes("recall") ||
      key.includes("relevance") ||
      key.includes("faithfulness") ||
      key.includes("rate") ||
      key.includes("coverage") ||
      key.includes("mrr")
    ) {
      return `${(value * 100).toFixed(1)}%`;
    }

    // Format count-based metrics
    if (key.includes("count") || key === "p_at_1") {
      return value.toFixed(0);
    }

    return value.toFixed(3);
  };

  const getMetricColor = (value: number, key: string) => {
    // Ensure value is a number
    if (typeof value !== "number" || isNaN(value)) {
      return "text-gray-600";
    }

    // Handle latency metrics (lower is better)
    if (key.includes("time") || key.includes("latency")) {
      return value < 1000
        ? "text-green-600"
        : value < 3000
        ? "text-yellow-600"
        : "text-red-600";
    }

    // Handle hallucination rate (lower is better)
    if (key.includes("hallucination_rate")) {
      return value < 0.1
        ? "text-green-600"
        : value < 0.3
        ? "text-yellow-600"
        : "text-red-600";
    }

    // Handle most quality metrics (higher is better)
    if (
      key.includes("score") ||
      key.includes("precision") ||
      key.includes("recall") ||
      key.includes("relevance") ||
      key.includes("faithfulness") ||
      key.includes("coverage") ||
      key.includes("mrr") ||
      key.includes("p_at_1")
    ) {
      return value > 0.8
        ? "text-green-600"
        : value > 0.6
        ? "text-yellow-600"
        : "text-red-600";
    }

    return "text-gray-600";
  };

  const getMetricDisplayName = (key: string) => {
    const displayNames: Record<string, string> = {
      precision_at_3: "Precision @ 3",
      precision_at_5: "Precision @ 5",
      mrr: "Mean Reciprocal Rank",
      p_at_1: "Precision @ 1",
      recall_at_100: "Recall @ 100",
      answer_relevance: "Answer Relevance",
      answer_faithfulness: "Answer Faithfulness",
      overall_score: "Overall Score",
      hallucination_rate: "Hallucination Rate",
      avg_response_time_ms: "Avg Response Time",
      retrieval_coverage: "Retrieval Coverage",
      retrieval_latency_global_p50_ms: "Retrieval Latency P50",
      retrieval_latency_global_p95_ms: "Retrieval Latency P95",
    };

    return (
      displayNames[key] ||
      key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())
    );
  };

  const getMetricDescription = (key: string) => {
    const descriptions: Record<string, string> = {
      recall_at_100:
        "Percentage of relevant documents found in top 100 results",
      retrieval_latency_global_p50_ms:
        "50th percentile of retrieval response times",
      retrieval_latency_global_p95_ms:
        "95th percentile of retrieval response times",
      precision_at_3: "Percentage of relevant documents in top 3 results",
      precision_at_5: "Percentage of relevant documents in top 5 results",
      mrr: "Mean reciprocal rank of first relevant document",
      p_at_1: "Precision at rank 1 (top result relevance)",
      answer_relevance: "How well the answer addresses the question",
      answer_faithfulness: "How faithful the answer is to source documents",
      overall_score: "Combined quality score across all metrics",
      hallucination_rate: "Percentage of answers with low faithfulness",
      avg_response_time_ms: "Average total response time",
      retrieval_coverage: "Percentage of queries that found relevant documents",
    };

    return descriptions[key] || "";
  };

  const getMetricIcon = (key: string) => {
    if (
      key.includes("precision") ||
      key.includes("recall") ||
      key.includes("mrr") ||
      key === "p_at_1"
    ) {
      return Target;
    }
    if (
      key.includes("relevance") ||
      key.includes("faithfulness") ||
      key.includes("score")
    ) {
      return Award;
    }
    if (key.includes("time") || key.includes("latency")) {
      return Clock;
    }
    if (key.includes("rate") || key.includes("coverage")) {
      return Activity;
    }
    return TrendingUp;
  };

  const categorizeMetrics = (metrics: Record<string, number>) => {
    const categories = {
      "Retrieval Metrics": {} as Record<string, number>,
      "Answer Quality": {} as Record<string, number>,
      Performance: {} as Record<string, number>,
      Overall: {} as Record<string, number>,
    };

    Object.entries(metrics).forEach(([key, value]) => {
      if (
        key.includes("precision") ||
        key.includes("recall") ||
        key.includes("mrr") ||
        key.includes("coverage") ||
        key === "p_at_1"
      ) {
        categories["Retrieval Metrics"][key] = value;
      } else if (
        key.includes("relevance") ||
        key.includes("faithfulness") ||
        key.includes("hallucination")
      ) {
        categories["Answer Quality"][key] = value;
      } else if (key.includes("time") || key.includes("latency")) {
        categories["Performance"][key] = value;
      } else {
        categories["Overall"][key] = value;
      }
    });

    // Remove empty categories
    return Object.fromEntries(
      Object.entries(categories).filter(
        ([_, metrics]) => Object.keys(metrics).length > 0
      )
    );
  };

  const handleRunSelection = (runName: string) => {
    if (compareMode) {
      if (selectedForComparison.includes(runName)) {
        setSelectedForComparison((prev) =>
          prev.filter((name) => name !== runName)
        );
      } else if (selectedForComparison.length < 2) {
        setSelectedForComparison((prev) => [...prev, runName]);
      }
    } else {
      fetchRunDetails(runName);
    }
  };

  const startComparison = () => {
    if (selectedForComparison.length === 2) {
      compareRuns(selectedForComparison[0], selectedForComparison[1]);
      setCompareMode(false);
      setSelectedForComparison([]);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white/30 p-6"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-gradient-to-r from-primary-500 to-primary-600 p-3 rounded-lg">
              <BarChart className="h-6 w-6 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-800">
                Evaluation Dashboard
              </h2>
              <p className="text-gray-600">
                Monitor and compare evaluation runs
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <motion.button
              onClick={() => {
                setCompareMode(!compareMode);
                setSelectedForComparison([]);
              }}
              className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 flex items-center space-x-2 ${
                compareMode
                  ? "bg-red-100 text-red-700 border border-red-200"
                  : "bg-blue-100 text-blue-700 border border-blue-200"
              }`}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {compareMode ? (
                <X className="h-4 w-4" />
              ) : (
                <GitCompare className="h-4 w-4" />
              )}
              <span>{compareMode ? "Cancel" : "Compare"}</span>
            </motion.button>

            <motion.button
              onClick={fetchRuns}
              disabled={loading}
              className="px-4 py-2 bg-gradient-to-r from-primary-500 to-primary-600 text-white rounded-lg font-medium hover:from-primary-600 hover:to-primary-700 disabled:opacity-50 flex items-center space-x-2"
              whileHover={{ scale: loading ? 1 : 1.02 }}
              whileTap={{ scale: loading ? 1 : 0.98 }}
            >
              <RefreshCw
                className={`h-4 w-4 ${loading ? "animate-spin" : ""}`}
              />
              <span>Refresh</span>
            </motion.button>
          </div>
        </div>

        {/* Search and Filter */}
        <div className="mt-6 flex items-center space-x-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search evaluation runs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
          </div>

          {compareMode && (
            <motion.button
              onClick={startComparison}
              disabled={selectedForComparison.length !== 2}
              className="px-4 py-2 bg-green-600 text-white rounded-lg font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              whileHover={{
                scale: selectedForComparison.length === 2 ? 1.02 : 1,
              }}
              whileTap={{
                scale: selectedForComparison.length === 2 ? 0.98 : 1,
              }}
            >
              <GitCompare className="h-4 w-4" />
              <span>Compare Selected ({selectedForComparison.length}/2)</span>
            </motion.button>
          )}
        </div>
      </motion.div>

      {/* Navigation */}
      <div className="flex items-center space-x-2 bg-white/70 backdrop-blur-md rounded-xl p-1">
        {["overview", "details", "compare", "run"].map((view) => (
          <motion.button
            key={view}
            onClick={() => setActiveView(view as any)}
            className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 capitalize ${
              activeView === view
                ? "bg-primary-500 text-white shadow-md"
                : "text-gray-600 hover:text-gray-800 hover:bg-white/50"
            }`}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {view}
          </motion.button>
        ))}
      </div>

      {/* Error Display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center space-x-3"
          >
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
            <span className="text-red-700">{error}</span>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-red-600 hover:text-red-800"
            >
              <X className="h-4 w-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <AnimatePresence mode="wait">
        {activeView === "overview" && (
          <motion.div
            key="overview"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="grid gap-6"
          >
            {/* Runs List */}
            <div className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white/30 overflow-hidden">
              <div className="p-6 border-b border-gray-200/50">
                <h3 className="text-lg font-semibold text-gray-800">
                  Recent Evaluation Runs
                </h3>
                <p className="text-sm text-gray-600 mt-1">
                  {filteredRuns.length} runs found
                </p>
              </div>

              <div className="divide-y divide-gray-200/50">
                {loading && (
                  <div className="p-8 text-center">
                    <Loader className="h-8 w-8 animate-spin text-primary-500 mx-auto mb-3" />
                    <p className="text-gray-600">Loading evaluation runs...</p>
                  </div>
                )}

                {!loading && filteredRuns.length === 0 && (
                  <div className="p-8 text-center">
                    <BarChart className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-gray-600">No evaluation runs found</p>
                  </div>
                )}

                {!loading &&
                  filteredRuns.map((run, index) => (
                    <motion.div
                      key={run.name}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className={`p-4 hover:bg-gray-50/50 transition-all duration-200 ${
                        compareMode && selectedForComparison.includes(run.name)
                          ? "bg-blue-50 border-l-4 border-blue-500"
                          : ""
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div
                          className="flex items-center space-x-3 flex-1 cursor-pointer"
                          onClick={() => handleRunSelection(run.name)}
                        >
                          {compareMode ? (
                            <div
                              className={`w-4 h-4 rounded border-2 ${
                                selectedForComparison.includes(run.name)
                                  ? "bg-blue-500 border-blue-500"
                                  : "border-gray-300"
                              }`}
                            >
                              {selectedForComparison.includes(run.name) && (
                                <CheckCircle className="h-3 w-3 text-white" />
                              )}
                            </div>
                          ) : (
                            <Eye className="h-4 w-4 text-gray-400" />
                          )}

                          <div>
                            <h4 className="font-medium text-gray-800">
                              {run.name}
                            </h4>
                            <div className="flex items-center space-x-2 text-sm text-gray-500">
                              <Clock className="h-3 w-3" />
                              <span>{formatTimestamp(run.ts)}</span>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2">
                          {!compareMode && (
                            <>
                              <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-full">
                                View Details
                              </span>
                              <motion.button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setRunToDelete(run.name);
                                  setShowDeleteConfirm(true);
                                }}
                                className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                whileHover={{ scale: 1.1 }}
                                whileTap={{ scale: 0.9 }}
                                title="Delete run"
                              >
                                <Trash2 className="h-4 w-4" />
                              </motion.button>
                            </>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))}
              </div>
            </div>
          </motion.div>
        )}

        {activeView === "details" && selectedRun && (
          <motion.div
            key="details"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="space-y-6"
          >
            {/* Run Details Header */}
            <div className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white/30 p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-xl font-bold text-gray-800">
                    {selectedRun.name}
                  </h3>
                  <p className="text-gray-600">
                    {formatTimestamp(selectedRun.ts)}
                  </p>
                </div>
                <motion.button
                  onClick={() => setActiveView("overview")}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Back to Overview
                </motion.button>
              </div>

              {/* Metadata */}
              {Object.keys(selectedRun.meta).length > 0 && (
                <div className="bg-gray-50/80 rounded-lg p-4">
                  <h4 className="font-medium text-gray-800 mb-2">Metadata</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    {Object.entries(selectedRun.meta).map(([key, value]) => (
                      <div key={key}>
                        <span className="text-gray-600">{key}:</span>
                        <span className="ml-2 font-medium">
                          {String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Metrics Grid */}
            <div className="space-y-6">
              {Object.entries(categorizeMetrics(selectedRun.metrics)).map(
                ([category, metrics]) => (
                  <div key={category} className="space-y-4">
                    <h3 className="text-lg font-semibold text-gray-800 border-b border-gray-200 pb-2">
                      {category}
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {Object.entries(metrics).map(([key, value]) => (
                        <motion.div
                          key={key}
                          initial={{ opacity: 0, scale: 0.95 }}
                          animate={{ opacity: 1, scale: 1 }}
                          className="bg-white/90 backdrop-blur-xl rounded-xl shadow-lg border border-white/30 p-4"
                          title={getMetricDescription(key)}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="text-sm font-medium text-gray-600">
                              {getMetricDisplayName(key)}
                            </h4>
                            {React.createElement(getMetricIcon(key), {
                              className: `h-4 w-4 ${getMetricColor(
                                value,
                                key
                              )}`,
                            })}
                          </div>
                          <p
                            className={`text-2xl font-bold ${getMetricColor(
                              value,
                              key
                            )}`}
                          >
                            {formatMetricValue(value, key)}
                          </p>
                        </motion.div>
                      ))}
                    </div>
                  </div>
                )
              )}
            </div>

            {/* Samples */}
            {selectedRun.samples.length > 0 && (
              <div className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white/30 overflow-hidden">
                <div className="p-6 border-b border-gray-200/50">
                  <h3 className="text-lg font-semibold text-gray-800">
                    Sample Results
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    {selectedRun.samples.length} samples
                  </p>
                </div>
                <div className="max-h-64 overflow-y-auto p-6 space-y-4">
                  {selectedRun.samples.slice(0, 10).map((sample, index) => (
                    <div
                      key={index}
                      className="bg-gray-50/80 rounded-lg p-4 text-sm"
                    >
                      <pre className="whitespace-pre-wrap text-gray-700">
                        {JSON.stringify(sample, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}

        {activeView === "compare" && comparison && (
          <motion.div
            key="compare"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="space-y-6"
          >
            {/* Comparison Header */}
            <div className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white/30 p-6">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-bold text-gray-800">
                  Run Comparison
                </h3>
                <motion.button
                  onClick={() => setActiveView("overview")}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Back to Overview
                </motion.button>
              </div>
            </div>

            {/* Metrics Comparison */}
            <div className="space-y-4">
              {Object.entries(comparison.diffs).map(([metric, data]) => (
                <motion.div
                  key={metric}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-white/90 backdrop-blur-xl rounded-xl shadow-lg border border-white/30 p-6"
                >
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-lg font-medium text-gray-800">
                      {getMetricDisplayName(metric)}
                    </h4>
                    <div className="flex items-center space-x-2">
                      {data.delta > 0 ? (
                        <TrendingUp className="h-5 w-5 text-green-600" />
                      ) : data.delta < 0 ? (
                        <TrendingDown className="h-5 w-5 text-red-600" />
                      ) : (
                        <div className="h-5 w-5" />
                      )}
                      <span
                        className={`font-bold ${
                          data.delta > 0
                            ? "text-green-600"
                            : data.delta < 0
                            ? "text-red-600"
                            : "text-gray-600"
                        }`}
                      >
                        {data.delta > 0 ? "+" : ""}
                        {data.pct_change.toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div className="bg-gray-50/80 rounded-lg p-3">
                      <p className="text-sm text-gray-600">Base</p>
                      <p className="text-lg font-bold text-gray-800">
                        {formatMetricValue(data.base, metric)}
                      </p>
                    </div>
                    <div className="bg-blue-50/80 rounded-lg p-3">
                      <p className="text-sm text-gray-600">Experiment</p>
                      <p className="text-lg font-bold text-blue-800">
                        {formatMetricValue(data.exp, metric)}
                      </p>
                    </div>
                    <div
                      className={`rounded-lg p-3 ${
                        data.delta > 0
                          ? "bg-green-50/80"
                          : data.delta < 0
                          ? "bg-red-50/80"
                          : "bg-gray-50/80"
                      }`}
                    >
                      <p className="text-sm text-gray-600">Delta</p>
                      <p
                        className={`text-lg font-bold ${
                          data.delta > 0
                            ? "text-green-800"
                            : data.delta < 0
                            ? "text-red-800"
                            : "text-gray-800"
                        }`}
                      >
                        {data.delta > 0 ? "+" : ""}
                        {formatMetricValue(Math.abs(data.delta), metric)}
                      </p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {activeView === "run" && (
          <motion.div
            key="run"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="space-y-6"
          >
            <div className="bg-white/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white/30 p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-xl font-bold text-gray-800">
                    Run New Evaluation
                  </h3>
                  <p className="text-gray-600">
                    Execute and store a new evaluation run
                  </p>
                </div>
                <motion.button
                  onClick={() => setActiveView("overview")}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Back to Overview
                </motion.button>
              </div>

              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (!runForm.name.trim()) {
                    setError("Evaluation name is required");
                    return;
                  }
                  try {
                    await runAndStoreEvaluation(
                      runForm.name,
                      runForm.limit,
                      runForm.created_by || undefined,
                      runForm.question_type
                    );
                    setActiveView("overview");
                  } catch (err) {
                    // Error is already set by runAndStoreEvaluation
                  }
                }}
                className="space-y-6"
              >
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Question Type *
                    </label>
                    <select
                      value={runForm.question_type}
                      onChange={(e) =>
                        setRunForm((prev) => ({
                          ...prev,
                          question_type: e.target.value,
                        }))
                      }
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    >
                      <option value="easy">Easy Questions</option>
                      <option value="hard">Hard Questions</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Evaluation Name *
                    </label>
                    <input
                      type="text"
                      value={runForm.name}
                      onChange={(e) =>
                        setRunForm((prev) => ({
                          ...prev,
                          name: e.target.value,
                        }))
                      }
                      placeholder="e.g., legal-qa-v1.2"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Question Limit
                    </label>
                    <input
                      type="number"
                      value={runForm.limit}
                      onChange={(e) =>
                        setRunForm((prev) => ({
                          ...prev,
                          limit: parseInt(e.target.value) || 100,
                        }))
                      }
                      min="1"
                      max="1000"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Created By (Optional)
                    </label>
                    <input
                      type="text"
                      value={runForm.created_by}
                      onChange={(e) =>
                        setRunForm((prev) => ({
                          ...prev,
                          created_by: e.target.value,
                        }))
                      }
                      placeholder="e.g., john.doe@company.com"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between pt-6 border-t border-gray-200">
                  <div className="text-sm text-gray-600">
                    This will execute {runForm.limit} evaluation questions and
                    store the results
                  </div>
                  <div className="flex items-center space-x-3">
                    <motion.button
                      type="button"
                      onClick={() => {
                        setRunForm({
                          name: "",
                          limit: 100,
                          created_by: "",
                          question_type: "easy",
                        });
                        setActiveView("overview");
                      }}
                      className="px-6 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      Cancel
                    </motion.button>
                    <motion.button
                      type="submit"
                      disabled={isRunning || !runForm.name.trim()}
                      className="px-6 py-3 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg font-medium hover:from-green-600 hover:to-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                      whileHover={{ scale: isRunning ? 1 : 1.02 }}
                      whileTap={{ scale: isRunning ? 1 : 0.98 }}
                    >
                      {isRunning ? (
                        <>
                          <Loader className="h-4 w-4 animate-spin" />
                          <span>Running...</span>
                        </>
                      ) : (
                        <>
                          <Play className="h-4 w-4" />
                          <span>Run Evaluation</span>
                        </>
                      )}
                    </motion.button>
                  </div>
                </div>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Run New Evaluation Modal */}
      <AnimatePresence>
        {showRunForm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowRunForm(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white/95 backdrop-blur-xl rounded-2xl shadow-2xl border border-white/30 p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-bold text-gray-800">Quick Run</h3>
                <button
                  onClick={() => setShowRunForm(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (!runForm.name.trim()) {
                    setError("Evaluation name is required");
                    return;
                  }
                  try {
                    await runAndStoreEvaluation(
                      runForm.name,
                      runForm.limit,
                      runForm.created_by || undefined,
                      runForm.question_type
                    );
                  } catch (err) {
                    // Error is already set by runAndStoreEvaluation
                  }
                }}
                className="space-y-4"
              >
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Evaluation Name *
                  </label>
                  <input
                    type="text"
                    value={runForm.name}
                    onChange={(e) =>
                      setRunForm((prev) => ({ ...prev, name: e.target.value }))
                    }
                    placeholder="e.g., legal-qa-v1.2"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Question Limit
                  </label>
                  <input
                    type="number"
                    value={runForm.limit}
                    onChange={(e) =>
                      setRunForm((prev) => ({
                        ...prev,
                        limit: parseInt(e.target.value) || 100,
                      }))
                    }
                    min="1"
                    max="1000"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Created By (Optional)
                  </label>
                  <input
                    type="text"
                    value={runForm.created_by}
                    onChange={(e) =>
                      setRunForm((prev) => ({
                        ...prev,
                        created_by: e.target.value,
                      }))
                    }
                    placeholder="e.g., john.doe@company.com"
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>

                <div className="flex items-center justify-end space-x-3 pt-4">
                  <motion.button
                    type="button"
                    onClick={() => setShowRunForm(false)}
                    className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    Cancel
                  </motion.button>
                  <motion.button
                    type="submit"
                    disabled={isRunning || !runForm.name.trim()}
                    className="px-4 py-2 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg font-medium hover:from-green-600 hover:to-green-700 disabled:opacity-50 flex items-center space-x-2"
                    whileHover={{ scale: isRunning ? 1 : 1.02 }}
                    whileTap={{ scale: isRunning ? 1 : 0.98 }}
                  >
                    {isRunning ? (
                      <>
                        <Loader className="h-4 w-4 animate-spin" />
                        <span>Running...</span>
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4" />
                        <span>Run</span>
                      </>
                    )}
                  </motion.button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {showDeleteConfirm && runToDelete && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
            onClick={() => setShowDeleteConfirm(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center space-x-3 mb-4">
                <div className="bg-red-100 p-3 rounded-lg">
                  <AlertCircle className="h-6 w-6 text-red-600" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-800">
                    Delete Evaluation Run
                  </h3>
                  <p className="text-sm text-gray-600">
                    This action cannot be undone.
                  </p>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <p className="text-sm text-gray-700">
                  Are you sure you want to delete the evaluation run{" "}
                  <span className="font-medium text-gray-900">
                    "{runToDelete}"
                  </span>
                  ?
                </p>
              </div>

              <div className="flex items-center justify-end space-x-3">
                <motion.button
                  onClick={() => {
                    setShowDeleteConfirm(false);
                    setRunToDelete(null);
                  }}
                  className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  Cancel
                </motion.button>
                <motion.button
                  onClick={async () => {
                    try {
                      await deleteRun(runToDelete);
                      setShowDeleteConfirm(false);
                      setRunToDelete(null);
                    } catch (err) {
                      // Error handling is already done in deleteRun function
                      console.error("Delete failed:", err);
                    }
                  }}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center space-x-2"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Trash2 className="h-4 w-4" />
                  <span>Delete</span>
                </motion.button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default EvaluationDashboard;
