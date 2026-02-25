import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FiArrowLeft as ArrowLeft,
  FiRefreshCw as RefreshCw,
  FiClock as Clock,
  FiActivity as Activity,
  FiTrendingUp as TrendingUp,
  FiDatabase as Database,
  FiServer as Server,
  FiFilter as Filter,
} from "react-icons/fi";
import { useLatencySummary, useLatencyStats } from "../hooks/useLatencyData";
import type { LatencyStats } from "../types";

interface LatencyEntriesProps {
  onBack: () => void;
  userId?: string;
}

interface LatencyMetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}

const LatencyMetricCard: React.FC<LatencyMetricCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
}) => (
  <div className={`bg-white rounded-lg p-4 shadow-sm border-l-4 ${color}`}>
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-gray-600">{title}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
      </div>
      <Icon className="h-8 w-8 text-gray-400" />
    </div>
  </div>
);

interface EndpointRowProps {
  endpoint: string;
  stats: LatencyStats;
  onViewDetails: (endpoint: string) => void;
}

const EndpointRow: React.FC<EndpointRowProps> = ({
  endpoint,
  stats,
  onViewDetails,
}) => {
  const formatMs = (ms: number) => `${ms.toFixed(2)}ms`;
  const getPerformanceColor = (p95: number) => {
    if (p95 < 500) return "text-green-600";
    if (p95 < 1000) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <motion.tr
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="hover:bg-gray-50 cursor-pointer"
      onClick={() => onViewDetails(endpoint)}
    >
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <div className="h-10 w-10 rounded-lg bg-blue-100 flex items-center justify-center">
              <Server className="h-5 w-5 text-blue-600" />
            </div>
          </div>
          <div className="ml-4">
            <div className="text-sm font-medium text-gray-900">
              {endpoint.replace("/api/", "")}
            </div>
            <div className="text-sm text-gray-500">{stats.count} calls</div>
          </div>
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm text-gray-900">{formatMs(stats.median_ms)}</div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm text-gray-900">{formatMs(stats.mean_ms)}</div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div
          className={`text-sm font-medium ${getPerformanceColor(stats.p95_ms)}`}
        >
          {formatMs(stats.p95_ms)}
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div
          className={`text-sm font-medium ${getPerformanceColor(stats.p99_ms)}`}
        >
          {formatMs(stats.p99_ms)}
        </div>
      </td>
      <td className="px-6 py-4 whitespace-nowrap">
        <div className="text-sm text-gray-500">
          {formatMs(stats.min_ms)} - {formatMs(stats.max_ms)}
        </div>
      </td>
    </motion.tr>
  );
};

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
  const [selectedEndpoint, setSelectedEndpoint] = useState<string | null>(null);
  const [dataSource, setDataSource] = useState<"memory" | "database">(
    "database",
  );
  const [hoursBack, setHoursBack] = useState<number | null>(24);
  const [typeCategory, setTypeCategory] = useState<string>("");

  const {
    data: summaryData,
    loading: summaryLoading,
    error: summaryError,
    refetch: refetchSummary,
  } = useLatencySummary({
    source: dataSource,
    hoursBack,
    typeCategory: typeCategory || undefined,
    refreshInterval: 30000, // Refresh every 30 seconds
  });

  const { data: endpointStats, refetch: refetchEndpoint } = useLatencyStats(
    selectedEndpoint || "",
    userId,
    {
      source: dataSource,
      hoursBack,
      typeCategory: typeCategory || undefined,
    },
  );

  const handleRefresh = () => {
    refetchSummary();
    if (selectedEndpoint) {
      refetchEndpoint();
    }
  };

  const calculateOverallStats = () => {
    if (!summaryData?.endpoints) return null;

    const allEndpoints = Object.values(summaryData.endpoints);
    if (allEndpoints.length === 0) return null;

    const totalCalls = allEndpoints.reduce(
      (sum, stats) => sum + stats.count,
      0,
    );
    const avgMedian =
      allEndpoints.reduce((sum, stats) => sum + stats.median_ms, 0) /
      allEndpoints.length;
    const maxP95 = Math.max(...allEndpoints.map((stats) => stats.p95_ms));
    const maxP99 = Math.max(...allEndpoints.map((stats) => stats.p99_ms));

    return {
      totalCalls,
      avgMedian,
      maxP95,
      maxP99,
      totalEndpoints: allEndpoints.length,
    };
  };

  const overallStats = calculateOverallStats();

  const renderEndpointDetails = () => {
    if (!selectedEndpoint || !endpointStats) return null;

    return (
      <motion.div
        initial={{ opacity: 0, x: 300 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 300 }}
        className="bg-white rounded-lg shadow-sm p-6 border"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Endpoint Details: {selectedEndpoint.replace("/api/", "")}
          </h3>
          <button
            onClick={() => setSelectedEndpoint(null)}
            className="text-gray-400 hover:text-gray-600"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <LatencyMetricCard
            title="Total Calls"
            value={endpointStats.stats.count.toString()}
            icon={Activity}
            color="border-blue-500"
          />
          <LatencyMetricCard
            title="Median"
            value={`${endpointStats.stats.median_ms.toFixed(2)}ms`}
            icon={Clock}
            color="border-green-500"
          />
          <LatencyMetricCard
            title="P95"
            value={`${endpointStats.stats.p95_ms.toFixed(2)}ms`}
            icon={TrendingUp}
            color="border-yellow-500"
          />
          <LatencyMetricCard
            title="P99"
            value={`${endpointStats.stats.p99_ms.toFixed(2)}ms`}
            icon={TrendingUp}
            color="border-red-500"
          />
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            Additional Metrics
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Mean:</span>
              <span className="ml-2 font-medium">
                {endpointStats.stats.mean_ms.toFixed(2)}ms
              </span>
            </div>
            <div>
              <span className="text-gray-500">Min:</span>
              <span className="ml-2 font-medium">
                {endpointStats.stats.min_ms.toFixed(2)}ms
              </span>
            </div>
            <div>
              <span className="text-gray-500">Max:</span>
              <span className="ml-2 font-medium">
                {endpointStats.stats.max_ms.toFixed(2)}ms
              </span>
            </div>
          </div>
        </div>
      </motion.div>
    );
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
          {/* Data Source Toggle */}
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600">Source:</span>
            <select
              value={dataSource}
              onChange={(e) =>
                setDataSource(e.target.value as "memory" | "database")
              }
              className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="memory">Memory</option>
              <option value="database">Database</option>
            </select>
          </div>

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

          {/* Type Filter */}
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600">Type:</span>
            <select
              value={typeCategory}
              onChange={(e) => setTypeCategory(e.target.value)}
              className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Types</option>
              <option value="overall">Overall (Total request time)</option>
              <option value="response_start">
                Response Start (Time to first token)
              </option>
              <option value="API">API (Application logic)</option>
              <option value="LLM">LLM (Language model)</option>
              <option value="tool">Tool (External tools)</option>
            </select>
          </div>

          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={summaryLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw
              className={`h-4 w-4 ${summaryLoading ? "animate-spin" : ""}`}
            />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Overall Stats Cards */}
      {overallStats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <LatencyMetricCard
            title="Total Endpoints"
            value={overallStats.totalEndpoints.toString()}
            icon={Server}
            color="border-purple-500"
          />
          <LatencyMetricCard
            title="Total Calls"
            value={overallStats.totalCalls.toString()}
            icon={Activity}
            color="border-blue-500"
          />
          <LatencyMetricCard
            title="Avg Median"
            value={`${overallStats.avgMedian.toFixed(2)}ms`}
            icon={Clock}
            color="border-green-500"
          />
          <LatencyMetricCard
            title="Max P95"
            value={`${overallStats.maxP95.toFixed(2)}ms`}
            icon={TrendingUp}
            color="border-yellow-500"
          />
          <LatencyMetricCard
            title="Max P99"
            value={`${overallStats.maxP99.toFixed(2)}ms`}
            icon={TrendingUp}
            color="border-red-500"
          />
        </div>
      )}

      {/* Error Display */}
      {summaryError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Error loading latency data
              </h3>
              <div className="mt-2 text-sm text-red-700">{summaryError}</div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Endpoints Table */}
        <div className="xl:col-span-2">
          <div className="bg-white rounded-lg shadow-sm border">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">
                Endpoint Performance
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                {summaryData?.source === "database"
                  ? `${hoursBack === null ? "All entries" : `Last ${getTimeRangeLabel(hoursBack)}`} from database${typeCategory ? ` (${typeCategory} only)` : ""}`
                  : `Current session from memory${typeCategory ? ` (${typeCategory} only)` : ""}`}
              </p>
            </div>

            <div className="overflow-x-auto">
              {summaryLoading ? (
                <div className="flex items-center justify-center py-12">
                  <RefreshCw className="h-8 w-8 text-gray-400 animate-spin" />
                  <span className="ml-2 text-gray-600">
                    Loading latency data...
                  </span>
                </div>
              ) : !summaryData?.endpoints ||
                Object.keys(summaryData.endpoints).length === 0 ? (
                <div className="text-center py-12">
                  <Database className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">
                    No latency data found
                  </h3>
                  <p className="mt-1 text-sm text-gray-500">
                    No API calls have been tracked in the selected time period.
                  </p>
                </div>
              ) : (
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Endpoint
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Median
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Mean
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        P95
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        P99
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Min - Max
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    <AnimatePresence>
                      {Object.entries(summaryData.endpoints).map(
                        ([endpoint, stats]) => (
                          <EndpointRow
                            key={endpoint}
                            endpoint={endpoint}
                            stats={stats}
                            onViewDetails={setSelectedEndpoint}
                          />
                        ),
                      )}
                    </AnimatePresence>
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        {/* Endpoint Details Panel */}
        <div className="xl:col-span-1">
          <AnimatePresence mode="wait">
            {selectedEndpoint ? (
              renderEndpointDetails()
            ) : (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="bg-white rounded-lg shadow-sm p-6 border"
              >
                <div className="text-center">
                  <Filter className="mx-auto h-12 w-12 text-gray-400" />
                  <h3 className="mt-2 text-sm font-medium text-gray-900">
                    Select an endpoint
                  </h3>
                  <p className="mt-1 text-sm text-gray-500">
                    Click on any endpoint in the table to view detailed metrics.
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

export default LatencyEntries;
