import React, { useState, useEffect } from "react";
import {
  useCacheInfo,
  useCacheActions,
  useLatencyActions,
} from "../hooks/useCacheData";

interface CacheManagementProps {
  onDataCleared?: () => void;
}

const CacheManagement: React.FC<CacheManagementProps> = ({ onDataCleared }) => {
  const {
    data: cacheInfo,
    loading: infoLoading,
    error: infoError,
    refetch: refetchInfo,
  } = useCacheInfo();
  const {
    loading: cacheLoading,
    error: cacheError,
    lastAction: cacheAction,
    clearQueries,
    clearLatencyCache,
    clearAllCache,
  } = useCacheActions();

  const {
    loading: latencyLoading,
    error: latencyError,
    lastAction: latencyAction,
    clearAllLatency,
    clearMemoryLatency,
    clearDatabaseLatency,
  } = useLatencyActions();

  const [lastClearedMessage, setLastClearedMessage] = useState<string>("");
  const [preserveVectors, setPreserveVectors] = useState(true);

  // Fetch cache info on component mount only
  useEffect(() => {
    refetchInfo();
  }, []); // Empty dependency array - only run once on mount

  const handleClearQueries = async () => {
    const result = await clearQueries();
    if (result?.success) {
      setLastClearedMessage(`Cleared ${result.queries_cleared} cached queries`);
      refetchInfo();
      onDataCleared?.();
    }
  };

  const handleClearLatencyCache = async () => {
    const result = await clearLatencyCache();
    if (result?.success) {
      setLastClearedMessage(
        `Cleared ${result.latency_entries_cleared} latency cache entries`
      );
      refetchInfo();
      onDataCleared?.();
    }
  };

  const handleClearAllCache = async () => {
    if (!confirm("Are you sure you want to clear all cache data?")) return;

    const result = await clearAllCache(preserveVectors);
    if (result?.success) {
      setLastClearedMessage(result.message);
      refetchInfo();
      onDataCleared?.();
    }
  };

  const handleClearAllLatency = async () => {
    if (!confirm("Are you sure you want to clear all latency data?")) return;

    const result = await clearAllLatency();
    if (result?.success) {
      setLastClearedMessage(result.message);
      refetchInfo();
      onDataCleared?.();
    }
  };

  const handleClearMemoryLatency = async () => {
    const result = await clearMemoryLatency();
    if (result?.success) {
      setLastClearedMessage(result.message);
      refetchInfo();
      onDataCleared?.();
    }
  };

  const handleClearDatabaseLatency = async () => {
    if (!confirm("Are you sure you want to clear database latency records?"))
      return;

    const result = await clearDatabaseLatency();
    if (result?.success) {
      setLastClearedMessage(result.message);
      refetchInfo();
      onDataCleared?.();
    }
  };

  const isLoading = infoLoading || cacheLoading || latencyLoading;
  const currentError = infoError || cacheError || latencyError;
  const currentAction = cacheAction || latencyAction;

  return (
    <div className="bg-white rounded-lg shadow-lg p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Cache Management</h2>
        <button
          onClick={refetchInfo}
          disabled={isLoading}
          className="px-3 py-1 text-sm bg-blue-50 text-blue-600 rounded-md hover:bg-blue-100 disabled:opacity-50"
        >
          {infoLoading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {/* Cache Info */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">
          Cache Status
        </h3>
        {infoLoading ? (
          <div className="text-gray-600">Loading cache info...</div>
        ) : cacheInfo ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {cacheInfo.cache_info.total_keys}
              </div>
              <div className="text-sm text-gray-600">Total Keys</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {cacheInfo.cache_info.query_count}
              </div>
              <div className="text-sm text-gray-600">Cached Queries</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {cacheInfo.cache_info.latency_count}
              </div>
              <div className="text-sm text-gray-600">Latency Entries</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600">
                {cacheInfo.cache_info.other_count}
              </div>
              <div className="text-sm text-gray-600">Other Data</div>
            </div>
          </div>
        ) : (
          <div className="text-gray-600">No cache info available</div>
        )}

        {cacheInfo && (
          <div className="mt-3 text-sm text-gray-600">
            Storage: {cacheInfo.cache_info.using_redis ? "Redis" : "In-Memory"}
          </div>
        )}
      </div>

      {/* Status Messages */}
      {currentError && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <div className="text-red-700 text-sm">{currentError}</div>
        </div>
      )}

      {lastClearedMessage && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <div className="text-green-700 text-sm">{lastClearedMessage}</div>
        </div>
      )}

      {currentAction && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <div className="text-blue-700 text-sm">
            Currently {currentAction}...
          </div>
        </div>
      )}

      {/* Cache Actions */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-800">
          Cache Operations
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={handleClearQueries}
            disabled={isLoading}
            className="px-4 py-2 bg-yellow-600 text-white rounded-md hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Clear Query Cache
          </button>

          <button
            onClick={handleClearLatencyCache}
            disabled={isLoading}
            className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Clear Latency Cache
          </button>
        </div>
      </div>

      {/* Latency Data Actions */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-800">
          Latency Data Operations
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <button
            onClick={handleClearMemoryLatency}
            disabled={isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Clear Memory
          </button>

          <button
            onClick={handleClearDatabaseLatency}
            disabled={isLoading}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Clear Database
          </button>

          <button
            onClick={handleClearAllLatency}
            disabled={isLoading}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Clear All Latency
          </button>
        </div>
      </div>

      {/* Advanced Actions */}
      <div className="space-y-4 border-t pt-4">
        <h3 className="text-lg font-semibold text-gray-800">
          Advanced Operations
        </h3>

        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="preserveVectors"
              checked={preserveVectors}
              onChange={(e) => setPreserveVectors(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="preserveVectors" className="text-sm text-gray-700">
              Preserve vector embeddings (recommended)
            </label>
          </div>

          <button
            onClick={handleClearAllCache}
            disabled={isLoading}
            className="w-full px-4 py-3 bg-red-700 text-white rounded-md hover:bg-red-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            Clear All Cache Data
          </button>
        </div>
      </div>

      <div className="text-xs text-gray-500 bg-gray-50 rounded p-3">
        <p>
          <strong>Note:</strong> Clearing cached queries will force fresh
          responses for all future queries. Vector embeddings are expensive to
          compute and are preserved by default.
        </p>
      </div>
    </div>
  );
};

export default CacheManagement;
