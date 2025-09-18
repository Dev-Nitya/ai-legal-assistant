import React, { useState } from "react";
import { useLatencySummary, useLatencyStats } from "../hooks/useLatencyData";
import { MetricsCard } from "./MetricsCard";

interface LatencyDashboardProps {
  className?: string;
}

export const LatencyDashboard: React.FC<LatencyDashboardProps> = ({
  className = "",
}) => {
  const [selectedSource, setSelectedSource] = useState<"memory" | "database">(
    "memory"
  );
  const [selectedEndpoint, setSelectedEndpoint] =
    useState<string>("enhanced-chat");
  const [hoursBack, setHoursBack] = useState(24);

  const {
    data: summaryData,
    loading: summaryLoading,
    error: summaryError,
    refetch: refetchSummary,
  } = useLatencySummary({
    source: selectedSource,
    hoursBack,
    refreshInterval: 0, // Disable auto-refresh - manual only
  });

  const {
    data: endpointData,
    loading: endpointLoading,
    error: endpointError,
    refetch: refetchEndpoint,
  } = useLatencyStats(selectedEndpoint, undefined, {
    source: selectedSource,
    hoursBack,
    refreshInterval: 0, // Disable auto-refresh - manual only
  });

  const handleRefresh = () => {
    refetchSummary();
    refetchEndpoint();
  };

  const availableEndpoints = summaryData?.endpoints
    ? Object.keys(summaryData.endpoints)
    : [];

  if (summaryError || endpointError) {
    return (
      <div
        className={`bg-red-50 border border-red-200 rounded-lg p-4 ${className}`}
      >
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <span className="text-red-400">⚠️</span>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">
              Error loading latency data
            </h3>
            <div className="mt-2 text-sm text-red-700">
              {summaryError || endpointError}
            </div>
            <button
              onClick={handleRefresh}
              className="mt-2 text-sm bg-red-100 hover:bg-red-200 text-red-800 px-3 py-1 rounded"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-lg p-6">
        <h1 className="text-2xl font-bold mb-2">
          🚀 Latency Monitoring Dashboard
        </h1>
        <p className="text-blue-100">
          Real-time performance metrics for your API endpoints
        </p>
      </div>

      {/* Controls */}
      <div className="bg-white border border-gray-200 rounded-lg p-4">
        <div className="flex flex-wrap gap-4 items-center justify-between">
          <div className="flex flex-wrap gap-4 items-center">
            {/* Source Toggle */}
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium text-gray-700">
                Data Source:
              </label>
              <div className="flex border border-gray-300 rounded-lg overflow-hidden">
                <button
                  onClick={() => setSelectedSource("memory")}
                  className={`px-3 py-1 text-sm font-medium transition-colors ${
                    selectedSource === "memory"
                      ? "bg-blue-500 text-white"
                      : "bg-white text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  Memory
                </button>
                <button
                  onClick={() => setSelectedSource("database")}
                  className={`px-3 py-1 text-sm font-medium transition-colors ${
                    selectedSource === "database"
                      ? "bg-blue-500 text-white"
                      : "bg-white text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  Database
                </button>
              </div>
            </div>

            {/* Endpoint Selection */}
            {availableEndpoints.length > 0 && (
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700">
                  Endpoint:
                </label>
                <select
                  value={selectedEndpoint}
                  onChange={(e) => setSelectedEndpoint(e.target.value)}
                  className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {availableEndpoints.map((endpoint) => (
                    <option key={endpoint} value={endpoint}>
                      {endpoint.replace("-", " ")}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Time Range */}
            {selectedSource === "database" && (
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700">
                  Hours Back:
                </label>
                <select
                  value={hoursBack}
                  onChange={(e) => setHoursBack(Number(e.target.value))}
                  className="border border-gray-300 rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value={1}>1 hour</option>
                  <option value={6}>6 hours</option>
                  <option value={24}>24 hours</option>
                  <option value={168}>7 days</option>
                </select>
              </div>
            )}
          </div>

          {/* Refresh Button */}
          <button
            onClick={handleRefresh}
            disabled={summaryLoading || endpointLoading}
            className="flex items-center space-x-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-400 text-white px-4 py-2 rounded-lg transition-colors"
          >
            <span
              className={
                summaryLoading || endpointLoading ? "animate-spin" : ""
              }
            >
              🔄
            </span>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Loading State */}
      {(summaryLoading || endpointLoading) && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-2 text-gray-600">Loading metrics...</span>
        </div>
      )}

      {/* No Data State */}
      {!summaryLoading &&
        !endpointLoading &&
        (!summaryData?.endpoints ||
          Object.keys(summaryData.endpoints).length === 0) && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No latency data available
            </h3>
            <p className="text-gray-600 mb-4">
              Make some requests to /api/enhanced-chat to see metrics!
            </p>
            <button
              onClick={handleRefresh}
              className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg"
            >
              Check Again
            </button>
          </div>
        )}

      {/* Metrics Grid */}
      {!summaryLoading &&
        !endpointLoading &&
        summaryData?.endpoints &&
        Object.keys(summaryData.endpoints).length > 0 && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                All Endpoints Summary
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(summaryData.endpoints).map(
                  ([endpoint, stats]) => (
                    <MetricsCard
                      key={endpoint}
                      title={endpoint}
                      stats={stats}
                      source={summaryData.source}
                    />
                  )
                )}
              </div>
            </div>

            {/* Detailed View for Selected Endpoint */}
            {endpointData && (
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4">
                  Detailed View: {selectedEndpoint.replace("-", " ")}
                </h2>
                <div className="max-w-md">
                  <MetricsCard
                    title={endpointData.endpoint}
                    stats={endpointData.stats}
                    source={endpointData.source}
                  />
                </div>
              </div>
            )}
          </div>
        )}

      {/* Footer Info */}
      <div className="text-center text-sm text-gray-500 border-t border-gray-200 pt-4">
        <p>
          Manual refresh only (click Refresh button to update) • Last updated:{" "}
          {new Date().toLocaleTimeString()} •
          <a
            href="/api/latency/summary"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 hover:text-blue-600 ml-1"
          >
            View JSON API
          </a>
        </p>
      </div>
    </div>
  );
};
