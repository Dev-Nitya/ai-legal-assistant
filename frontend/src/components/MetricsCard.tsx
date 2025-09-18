import React from "react";
import type { LatencyStats } from "../types";

interface MetricsCardProps {
  title: string;
  stats: LatencyStats;
  source: "memory" | "database";
  className?: string;
}

const formatLatency = (ms: number): string => {
  if (ms < 1000) {
    return `${ms.toFixed(1)}ms`;
  } else {
    return `${(ms / 1000).toFixed(2)}s`;
  }
};

const getLatencyColor = (
  ms: number,
  type: "p95" | "p99" | "median"
): string => {
  if (type === "median") {
    return ms < 500
      ? "text-green-600"
      : ms < 1000
      ? "text-yellow-600"
      : "text-red-600";
  } else if (type === "p95") {
    return ms < 1000
      ? "text-green-600"
      : ms < 3000
      ? "text-yellow-600"
      : "text-red-600";
  } else {
    // p99
    return ms < 2000
      ? "text-green-600"
      : ms < 5000
      ? "text-yellow-600"
      : "text-red-600";
  }
};

export const MetricsCard: React.FC<MetricsCardProps> = ({
  title,
  stats,
  source,
  className = "",
}) => {
  const sourceBadgeClass =
    source === "memory"
      ? "bg-teal-100 text-teal-800"
      : "bg-orange-100 text-orange-800";

  const sourceLabel = source === "memory" ? "Redis/Memory" : "Database";

  return (
    <div
      className={`bg-white rounded-lg border border-gray-200 p-6 shadow-sm hover:shadow-md transition-shadow ${className}`}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 capitalize">
          📊 {title.replace("-", " ")}
        </h3>
        <span
          className={`px-2 py-1 rounded-full text-xs font-medium ${sourceBadgeClass}`}
        >
          {sourceLabel}
        </span>
      </div>

      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-gray-600">Count</span>
          <span className="text-sm font-bold text-gray-900">{stats.count}</span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-gray-600">Median</span>
          <span
            className={`text-sm font-bold ${getLatencyColor(
              stats.median_ms,
              "median"
            )}`}
          >
            {formatLatency(stats.median_ms)}
          </span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-gray-600">P95</span>
          <span
            className={`text-sm font-bold ${getLatencyColor(
              stats.p95_ms,
              "p95"
            )}`}
          >
            {formatLatency(stats.p95_ms)}
          </span>
        </div>

        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-gray-600">P99</span>
          <span
            className={`text-sm font-bold ${getLatencyColor(
              stats.p99_ms,
              "p99"
            )}`}
          >
            {formatLatency(stats.p99_ms)}
          </span>
        </div>

        <div className="pt-2 border-t border-gray-100">
          <div className="flex justify-between items-center text-xs text-gray-500">
            <span>Min: {formatLatency(stats.min_ms)}</span>
            <span>Max: {formatLatency(stats.max_ms)}</span>
          </div>
          <div className="flex justify-center mt-1">
            <span className="text-xs text-gray-500">
              Avg: {formatLatency(stats.mean_ms)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
