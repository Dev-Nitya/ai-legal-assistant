import { useState, useCallback } from 'react';

const API_BASE = '/api';

interface CacheInfo {
  using_redis: boolean;
  query_count: number;
  latency_count: number;
  other_count: number;
  total_keys: number;
}

interface CacheInfoResponse {
  success: boolean;
  message: string;
  cache_info: CacheInfo;
}

interface CacheActionResponse {
  success: boolean;
  message: string;
  queries_cleared?: number;
  latency_entries_cleared?: number;
  entries_cleared?: number;
  vectors_preserved?: boolean;
}

export const useCacheInfo = () => {
  const [data, setData] = useState<CacheInfoResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCacheInfo = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log('Fetching cache info');
      const response = await fetch(`${API_BASE}/cache/info`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result: CacheInfoResponse = await response.json();
      console.log('Cache info received:', result);
      setData(result);
    } catch (err) {
      console.error('Cache info fetch error:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch cache info');
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, refetch: fetchCacheInfo };
};

export const useCacheActions = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastAction, setLastAction] = useState<string | null>(null);

  const clearQueries = async (): Promise<CacheActionResponse | null> => {
    setLoading(true);
    setError(null);
    setLastAction('clearing queries');
    
    try {
      console.log('Clearing cached queries');
      const response = await fetch(`${API_BASE}/cache/clear-queries`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result: CacheActionResponse = await response.json();
      console.log('Queries cleared:', result);
      setLastAction(null);
      return result;
    } catch (err) {
      console.error('Clear queries error:', err);
      setError(err instanceof Error ? err.message : 'Failed to clear cached queries');
      setLastAction(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const clearLatencyCache = async (): Promise<CacheActionResponse | null> => {
    setLoading(true);
    setError(null);
    setLastAction('clearing latency cache');
    
    try {
      console.log('Clearing latency cache');
      const response = await fetch(`${API_BASE}/cache/clear-latency`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result: CacheActionResponse = await response.json();
      console.log('Latency cache cleared:', result);
      setLastAction(null);
      return result;
    } catch (err) {
      console.error('Clear latency cache error:', err);
      setError(err instanceof Error ? err.message : 'Failed to clear latency cache');
      setLastAction(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const clearAllCache = async (preserveVectors: boolean = true): Promise<CacheActionResponse | null> => {
    setLoading(true);
    setError(null);
    setLastAction('clearing all cache');
    
    try {
      console.log('Clearing all cache, preserve vectors:', preserveVectors);
      const params = new URLSearchParams({
        confirm: 'true',
        preserve_vectors: preserveVectors.toString(),
      });
      
      const response = await fetch(`${API_BASE}/cache/clear-all?${params}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result: CacheActionResponse = await response.json();
      console.log('All cache cleared:', result);
      setLastAction(null);
      return result;
    } catch (err) {
      console.error('Clear all cache error:', err);
      setError(err instanceof Error ? err.message : 'Failed to clear all cache');
      setLastAction(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return {
    loading,
    error,
    lastAction,
    clearQueries,
    clearLatencyCache,
    clearAllCache,
  };
};

export const useLatencyActions = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastAction, setLastAction] = useState<string | null>(null);

  const clearAllLatency = async (): Promise<CacheActionResponse | null> => {
    setLoading(true);
    setError(null);
    setLastAction('clearing all latency data');
    
    try {
      console.log('Clearing all latency data');
      const response = await fetch(`${API_BASE}/latency/clear-all?confirm=true`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result: CacheActionResponse = await response.json();
      console.log('All latency data cleared:', result);
      setLastAction(null);
      return result;
    } catch (err) {
      console.error('Clear all latency error:', err);
      setError(err instanceof Error ? err.message : 'Failed to clear all latency data');
      setLastAction(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const clearMemoryLatency = async (): Promise<CacheActionResponse | null> => {
    setLoading(true);
    setError(null);
    setLastAction('clearing memory latency');
    
    try {
      console.log('Clearing memory latency data');
      const response = await fetch(`${API_BASE}/latency/clear-memory`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result: CacheActionResponse = await response.json();
      console.log('Memory latency cleared:', result);
      setLastAction(null);
      return result;
    } catch (err) {
      console.error('Clear memory latency error:', err);
      setError(err instanceof Error ? err.message : 'Failed to clear memory latency');
      setLastAction(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const clearDatabaseLatency = async (): Promise<CacheActionResponse | null> => {
    setLoading(true);
    setError(null);
    setLastAction('clearing database latency');
    
    try {
      console.log('Clearing database latency data');
      const response = await fetch(`${API_BASE}/latency/clear-database?confirm=true`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result: CacheActionResponse = await response.json();
      console.log('Database latency cleared:', result);
      setLastAction(null);
      return result;
    } catch (err) {
      console.error('Clear database latency error:', err);
      setError(err instanceof Error ? err.message : 'Failed to clear database latency');
      setLastAction(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return {
    loading,
    error,
    lastAction,
    clearAllLatency,
    clearMemoryLatency,
    clearDatabaseLatency,
  };
};
