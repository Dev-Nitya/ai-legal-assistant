import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FiArrowLeft as ArrowLeft,
  FiRefreshCw as RefreshCw,
  FiClock as Clock,
  FiActivity as Activity,
  FiTrendingUp as TrendingUp,
  FiDatabase as Database,
} from "react-icons/fi";
import { useLatencyMeasurements } from "../hooks/useLatencyData";

interface LatencyEntriesProps {
  onBack: () => void;
  userId?: string;
}

interface LatencyMeasurement {
  id: number;
  endpoint: string;
  user_id?: string;
  latency_ms: number;
  timestamp: number;
  request_id?: string;
  type?: string;
  latency_metadata?: any;
}

interface RequestLatencyRow {
  request_id: string;
  timestamp: number;
  total_time?: number;
  response_start_time?: number;
  user_id?: string;
  query_analysis_time?: number;
  document_retrieval_time?: number;
  reranking_time?: number;
  tools_execution_time?: number;
  llm_generation_time?: number;
}

const getTimeRangeLabel = (hours: number): string => {
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"}`;
  if (hours < 168)
    return `${Math.floor(hours / 24)} day${Math.floor(hours / 24) === 1 ? "" : "s"}`;
  if (hours < 720)
    return `${Math.floor(hours / 168)} week${Math.floor(hours / 168) === 1 ? "" : "s"}`;
  if (hours < 8760)
    return `${Math.floor(hours / 720)} month${Math.floor(hours / 720) === 1 ? "" : "s"}`;
  return `${Math.floor(hours / 8760)} year${Math.floor(hours / 8760) === 1 ? "" : "s"}`;
};

const LatencyEntries: React.FC<LatencyEntriesProps> = ({ onBack, userId }) => {
  const [hoursBack, setHoursBack] = useState<number | null>(24);
  const [dataSource] = useState<"database">("database");

  // Get individual measurements for enhanced-chat endpoint
  const {
    data: measurementsData,
    loading: measurementsLoading,
    error: measurementsError,
    refetch: refetchMeasurements,
  } = useLatencyMeasurements("enhanced-chat", userId, {
    source: dataSource,
    hoursBack,
    limit: 100,
  });

  const handleRefresh = () => {
    refetchMeasurements();
  };

  // Process measurements to group by request_id and calculate stats
  const processLatencyData = () => {
    if (!measurementsData?.measurements) {
      return { requestRows: [], aggregateStats: null, phaseStats: null };
    }

    const measurements = measurementsData.measurements;

    // Group by request_id
    const requestGroups: { [key: string]: LatencyMeasurement[] } = {};
    measurements.forEach((measurement) => {
      const requestId = measurement.request_id || `single-${measurement.id}`;
      if (!requestGroups[requestId]) {
        requestGroups[requestId] = [];
      }
      requestGroups[requestId].push(measurement);
    });

    // Build request rows using proper type-based matching
    const requestRows: RequestLatencyRow[] = [];
    Object.entries(requestGroups).forEach(([requestId, measures]) => {
      const totalMeasurement = measures.find(
        (m) => m.type === "overall" || m.type === "API",
      );
      const responseStartMeasurement = measures.find(
        (m) => m.type === "response_start",
      );

      // Find phase timing measurements for this request
      const phaseTimings = measures.filter((m) => m.type === "phase_timing");
      const queryAnalysisTime = phaseTimings.find(
        (m) => m.latency_metadata?.phase === "query_analysis",
      )?.latency_ms;
      const documentRetrievalTime = phaseTimings.find(
        (m) => m.latency_metadata?.phase === "document_retrieval",
      )?.latency_ms;
      const rerankingTime = phaseTimings.find(
        (m) => m.latency_metadata?.phase === "reranking",
      )?.latency_ms;
      const toolsExecutionTime = phaseTimings.find(
        (m) => m.latency_metadata?.phase === "tools_execution",
      )?.latency_ms;
      const llmGenerationTime = phaseTimings.find(
        (m) => m.latency_metadata?.phase === "llm_generation",
      )?.latency_ms;

      // Only include requests that have at least one measurement
      if (totalMeasurement || responseStartMeasurement || measures.length > 0) {
        // If no type information available, use fallback logic
        const fallbackTotalTime =
          !totalMeasurement && !responseStartMeasurement && measures.length > 0
            ? Math.max(...measures.map((m) => m.latency_ms || 0))
            : undefined;

        requestRows.push({
          request_id: requestId,
          timestamp: Math.max(...measures.map((m) => m.timestamp)),
          total_time: totalMeasurement?.latency_ms || fallbackTotalTime,
          response_start_time: responseStartMeasurement?.latency_ms,
          user_id: measures[0].user_id,
          query_analysis_time: queryAnalysisTime,
          document_retrieval_time: documentRetrievalTime,
          reranking_time: rerankingTime,
          tools_execution_time: toolsExecutionTime,
          llm_generation_time: llmGenerationTime,
        });
      }
    });

    // Sort by timestamp (newest first)
    requestRows.sort((a, b) => b.timestamp - a.timestamp);

    // Calculate aggregate stats directly from raw measurements by type
    const responseStartMeasurements = measurements
      .filter((m) => m.type === "response_start")
      .map((m) => m.latency_ms);

    const totalTimeMeasurements = measurements
      .filter((m) => m.type === "overall" || m.type === "API")
      .map((m) => m.latency_ms);

    // Extract phase timing measurements
    const phaseTimingMeasurements = measurements.filter(
      (m) => m.type === "phase_timing",
    );

    const calculateStats = (values: number[]) => {
      if (values.length === 0) return null;

      const sorted = [...values].sort((a, b) => a - b);
      const median = sorted[Math.floor(sorted.length / 2)];
      const p95Index = Math.floor(sorted.length * 0.95);
      const p99Index = Math.floor(sorted.length * 0.99);

      return {
        count: values.length,
        median: median,
        p95: sorted[p95Index] || sorted[sorted.length - 1],
        p99: sorted[p99Index] || sorted[sorted.length - 1],
      };
    };

    const aggregateStats = {
      response_start_time: calculateStats(responseStartMeasurements),
      total_time: calculateStats(totalTimeMeasurements),
    };

    // Calculate phase-specific stats
    const phaseStats = {
      query_analysis: calculateStats(
        phaseTimingMeasurements
          .filter((m) => m.latency_metadata?.phase === "query_analysis")
          .map((m) => m.latency_ms),
      ),
      document_retrieval: calculateStats(
        phaseTimingMeasurements
          .filter((m) => m.latency_metadata?.phase === "document_retrieval")
          .map((m) => m.latency_ms),
      ),
      reranking: calculateStats(
        phaseTimingMeasurements
          .filter((m) => m.latency_metadata?.phase === "reranking")
          .map((m) => m.latency_ms),
      ),
      tools_execution: calculateStats(
        phaseTimingMeasurements
          .filter((m) => m.latency_metadata?.phase === "tools_execution")
          .map((m) => m.latency_ms),
      ),
      llm_generation: calculateStats(
        phaseTimingMeasurements
          .filter((m) => m.latency_metadata?.phase === "llm_generation")
          .map((m) => m.latency_ms),
      ),
    };

    // Debug logging to help diagnose missing phases
    console.log("Phase timing measurements:", phaseTimingMeasurements);
    console.log("Phase stats calculated:", phaseStats);

    return { requestRows, aggregateStats, phaseStats };
  };

  const { requestRows, aggregateStats, phaseStats } = processLatencyData();

  const formatMs = (ms: number | undefined) =>
    ms ? `${ms.toFixed(0)}ms` : "-";
  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleString();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button
            onClick={onBack}
            className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
            <span>Back to Cache Management</span>
          </button>
        </div>

        <div className="flex items-center space-x-4">
          {/* Time Range Filter */}
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600">Time Range:</span>
            <select
              value={hoursBack || "all"}
              onChange={(e) => {
                const value = e.target.value;
                setHoursBack(value === "all" ? null : parseInt(value));
              }}
              className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value={1}>1 Hour</option>
              <option value={6}>6 Hours</option>
              <option value={24}>24 Hours</option>
              <option value={72}>3 Days</option>
              <option value={168}>1 Week</option>
              <option value={720}>1 Month</option>
              <option value={2160}>3 Months</option>
              <option value={4320}>6 Months</option>
              <option value={8760}>1 Year</option>
              <option value="all">All Entries</option>
            </select>
          </div>

          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={measurementsLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw
              className={`h-4 w-4 ${measurementsLoading ? "animate-spin" : ""}`}
            />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Aggregate Stats Cards */}
      {aggregateStats &&
        (aggregateStats.total_time || aggregateStats.response_start_time) && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {aggregateStats.total_time && (
              <>
                <div className="bg-white rounded-lg p-4 shadow-sm border-l-4 border-blue-500">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">
                        Total Time - P95
                      </p>
                      <p className="text-2xl font-bold text-gray-900">
                        {formatMs(aggregateStats.total_time.p95)}
                      </p>
                      <p className="text-xs text-gray-500">
                        95th percentile ({aggregateStats.total_time.count}{" "}
                        requests)
                      </p>
                    </div>
                    <Clock className="h-8 w-8 text-gray-400" />
                  </div>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm border-l-4 border-yellow-500">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">
                        Total Time - P99
                      </p>
                      <p className="text-2xl font-bold text-gray-900">
                        {formatMs(aggregateStats.total_time.p99)}
                      </p>
                      <p className="text-xs text-gray-500">99th percentile</p>
                    </div>
                    <TrendingUp className="h-8 w-8 text-gray-400" />
                  </div>
                </div>
              </>
            )}
            {aggregateStats.response_start_time && (
              <>
                <div className="bg-white rounded-lg p-4 shadow-sm border-l-4 border-green-500">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">
                        Response Start - P95
                      </p>
                      <p className="text-2xl font-bold text-gray-900">
                        {formatMs(aggregateStats.response_start_time.p95)}
                      </p>
                      <p className="text-xs text-gray-500">
                        95th percentile (
                        {aggregateStats.response_start_time.count} requests)
                      </p>
                    </div>
                    <Activity className="h-8 w-8 text-gray-400" />
                  </div>
                </div>
                <div className="bg-white rounded-lg p-4 shadow-sm border-l-4 border-red-500">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-600">
                        Response Start - P99
                      </p>
                      <p className="text-2xl font-bold text-gray-900">
                        {formatMs(aggregateStats.response_start_time.p99)}
                      </p>
                      <p className="text-xs text-gray-500">99th percentile</p>
                    </div>
                    <TrendingUp className="h-8 w-8 text-gray-400" />
                  </div>
                </div>
              </>
            )}
          </div>
        )}

      {/* Phase Timing Statistics */}
      {phaseStats &&
        Object.values(phaseStats).some((stat) => stat !== null) && (
          <div className="bg-white rounded-lg shadow-sm border">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                Phase Performance Breakdown
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                Detailed timing for each processing phase (P95 values)
              </p>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {phaseStats.query_analysis && (
                  <div className="text-center p-4 bg-blue-50 rounded-lg">
                    <div className="text-sm font-medium text-gray-600 mb-1">
                      Query Analysis
                    </div>
                    <div className="text-xl font-bold text-blue-600">
                      {formatMs(phaseStats.query_analysis.p95)}
                    </div>
                    <div className="text-xs text-gray-500">
                      {phaseStats.query_analysis.count} measurements
                    </div>
                  </div>
                )}
                {phaseStats.document_retrieval && (
                  <div className="text-center p-4 bg-green-50 rounded-lg">
                    <div className="text-sm font-medium text-gray-600 mb-1">
                      Document Retrieval
                    </div>
                    <div className="text-xl font-bold text-green-600">
                      {formatMs(phaseStats.document_retrieval.p95)}
                    </div>
                    <div className="text-xs text-gray-500">
                      {phaseStats.document_retrieval.count} measurements
                    </div>
                  </div>
                )}
                {phaseStats.reranking && (
                  <div className="text-center p-4 bg-yellow-50 rounded-lg">
                    <div className="text-sm font-medium text-gray-600 mb-1">
                      Re-ranking
                    </div>
                    <div className="text-xl font-bold text-yellow-600">
                      {formatMs(phaseStats.reranking.p95)}
                    </div>
                    <div className="text-xs text-gray-500">
                      {phaseStats.reranking.count} measurements
                    </div>
                  </div>
                )}
                {phaseStats.tools_execution && (
                  <div className="text-center p-4 bg-purple-50 rounded-lg">
                    <div className="text-sm font-medium text-gray-600 mb-1">
                      Tools Execution
                    </div>
                    <div className="text-xl font-bold text-purple-600">
                      {formatMs(phaseStats.tools_execution.p95)}
                    </div>
                    <div className="text-xs text-gray-500">
                      {phaseStats.tools_execution.count} measurements
                    </div>
                  </div>
                )}
                {phaseStats.llm_generation && (
                  <div className="text-center p-4 bg-red-50 rounded-lg">
                    <div className="text-sm font-medium text-gray-600 mb-1">
                      LLM Generation
                    </div>
                    <div className="text-xl font-bold text-red-600">
                      {formatMs(phaseStats.llm_generation.p95)}
                    </div>
                    <div className="text-xs text-gray-500">
                      {phaseStats.llm_generation.count} measurements
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

      {/* Error Display */}
      {measurementsError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Error loading latency data
              </h3>
              <div className="mt-2 text-sm text-red-700">
                {measurementsError}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Request Table */}
      <div className="bg-white rounded-lg shadow-sm border">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            Request Latencies
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Individual request performance for{" "}
            {hoursBack === null
              ? "all entries"
              : `the last ${getTimeRangeLabel(hoursBack)}`}
          </p>
        </div>

        <div className="overflow-x-auto">
          {measurementsLoading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-8 w-8 text-gray-400 animate-spin" />
              <span className="ml-2 text-gray-600">
                Loading latency data...
              </span>
            </div>
          ) : requestRows.length === 0 ? (
            <div className="text-center py-12">
              <Database className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">
                No request data found
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                No requests have been tracked in the selected time period.
              </p>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Request Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Request ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Query Analysis
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Retrieval
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Reranking
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tools
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    LLM Gen
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Response Start
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                <AnimatePresence>
                  {requestRows.map((row, index) => (
                    <motion.tr
                      key={row.request_id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      transition={{ delay: index * 0.05 }}
                      className="hover:bg-gray-50"
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatTimestamp(row.timestamp)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-600">
                        {row.request_id.substring(0, 12)}...
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-medium text-blue-600">
                          {formatMs(row.query_analysis_time)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-medium text-green-600">
                          {formatMs(row.document_retrieval_time)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-medium text-yellow-600">
                          {formatMs(row.reranking_time)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-medium text-purple-600">
                          {formatMs(row.tools_execution_time)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-medium text-red-600">
                          {formatMs(row.llm_generation_time)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`text-sm font-medium ${
                            row.response_start_time &&
                            row.response_start_time < 1000
                              ? "text-green-600"
                              : row.response_start_time &&
                                  row.response_start_time < 2000
                                ? "text-yellow-600"
                                : "text-red-600"
                          }`}
                        >
                          {formatMs(row.response_start_time)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`text-sm font-medium ${
                            row.total_time && row.total_time < 5000
                              ? "text-green-600"
                              : row.total_time && row.total_time < 10000
                                ? "text-yellow-600"
                                : "text-red-600"
                          }`}
                        >
                          {formatMs(row.total_time)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {row.user_id || "Anonymous"}
                      </td>
                    </motion.tr>
                  ))}
                </AnimatePresence>
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

export default LatencyEntries;
