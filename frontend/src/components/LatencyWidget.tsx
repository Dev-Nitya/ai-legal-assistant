import React from "react";
import { useLatencyStats } from "../hooks/useLatencyData";

interface LatencyWidgetProps {
  endpoint: string;
  userId?: string;
  compact?: boolean;
  className?: string;
}

const formatLatency = (ms: number): string => {
  if (ms < 1000) {
    return `${ms.toFixed(0)}ms`;
  } else {
    return `${(ms / 1000).toFixed(1)}s`;
  }
};

const getStatusColor = (p95: number): string => {
  if (p95 < 1000) return "text-green-600 bg-green-50";
  if (p95 < 3000) return "text-yellow-600 bg-yellow-50";
  return "text-red-600 bg-red-50";
};

export const LatencyWidget: React.FC<LatencyWidgetProps> = ({
  endpoint,
  userId,
  compact = false,
  className = "",
}) => {
  const { data, loading, error } = useLatencyStats(endpoint, userId, {
    source: "memory",
    refreshInterval: 0, // Disable auto-refresh to avoid continuous polling
  });

  if (loading) {
    return (
      <div className={`inline-flex items-center space-x-2 ${className}`}>
        <div className="animate-pulse w-2 h-2 bg-gray-400 rounded-full"></div>
        <span className="text-xs text-gray-500">Loading...</span>
      </div>
    );
  }

  if (error || !data?.stats) {
    return (
      <div className={`inline-flex items-center space-x-2 ${className}`}>
        <div className="w-2 h-2 bg-red-500 rounded-full"></div>
        <span className="text-xs text-red-600">Metrics unavailable</span>
      </div>
    );
  }

  const { stats } = data;
  const statusColor = getStatusColor(stats.p95_ms);

  if (compact) {
    return (
      <div className={`inline-flex items-center space-x-2 ${className}`}>
        <div
          className={`w-2 h-2 rounded-full ${statusColor.split(" ")[1]}`}
        ></div>
        <span className={`text-xs font-medium ${statusColor.split(" ")[0]}`}>
          P95: {formatLatency(stats.p95_ms)}
        </span>
      </div>
    );
  }

  return (
    <div
      className={`inline-flex items-center space-x-3 px-3 py-2 rounded-lg border ${statusColor} ${className}`}
    >
      <div className="flex items-center space-x-2">
        <div
          className={`w-2 h-2 rounded-full ${statusColor.split(" ")[1]}`}
        ></div>
        <span className="text-xs font-medium text-gray-700">
          {endpoint.replace("-", " ")}
        </span>
      </div>

      <div className="flex items-center space-x-3 text-xs">
        <span className="font-medium">
          P95:{" "}
          <span className={statusColor.split(" ")[0]}>
            {formatLatency(stats.p95_ms)}
          </span>
        </span>
        <span className="font-medium">
          P99:{" "}
          <span className={statusColor.split(" ")[0]}>
            {formatLatency(stats.p99_ms)}
          </span>
        </span>
        <span className="text-gray-500">({stats.count} samples)</span>
      </div>
    </div>
  );
};
