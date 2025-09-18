import { useState, useEffect } from 'react';
import type { LatencyStatsResponse, EndpointSummaryResponse, LatencyMeasurementsResponse } from '../types';

const API_BASE = 'http://localhost:8000/api';

interface UseLatencyDataOptions {
  refreshInterval?: number; // milliseconds
  source?: 'memory' | 'database';
  hoursBack?: number;
}

export const useLatencyStats = (endpoint: string, userId?: string, options: UseLatencyDataOptions = {}) => {
  const [data, setData] = useState<LatencyStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { refreshInterval = 0, source = 'memory', hoursBack = 24 } = options;

  const fetchData = async () => {
    try {
      setError(null);
      console.log(`Fetching latency stats for endpoint: ${endpoint}`); // Debug log
      
      const params = new URLSearchParams({
        source,
        hours_back: hoursBack.toString(),
        ...(userId && { user_id: userId }),
      });

      const url = `${API_BASE}/latency/stats/${endpoint}?${params}`;
      console.log(`Making request to: ${url}`); // Debug log
      
      const response = await fetch(url);
      
      console.log(`Response status: ${response.status}`); // Debug log
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result: LatencyStatsResponse = await response.json();
      console.log('Received data:', result); // Debug log
      setData(result);
    } catch (err) {
      console.error('Fetch error:', err); // Debug log
      setError(err instanceof Error ? err.message : 'Failed to fetch latency stats');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Set up auto-refresh only if refreshInterval > 0
    if (refreshInterval > 0) {
      const interval = setInterval(fetchData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [endpoint, userId, source, hoursBack, refreshInterval]);

  return { data, loading, error, refetch: fetchData };
};

export const useLatencySummary = (options: UseLatencyDataOptions = {}) => {
  const [data, setData] = useState<EndpointSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { refreshInterval = 0, source = 'memory', hoursBack = 24 } = options;

  const fetchData = async () => {
    try {
      setError(null);
      console.log('Fetching latency summary'); // Debug log
      
      const params = new URLSearchParams({
        source,
        hours_back: hoursBack.toString(),
      });

      const url = `${API_BASE}/latency/summary?${params}`;
      console.log(`Making request to: ${url}`); // Debug log

      const response = await fetch(url);
      
      console.log(`Response status: ${response.status}`); // Debug log
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result: EndpointSummaryResponse = await response.json();
      console.log('Received summary data:', result); // Debug log
      setData(result);
    } catch (err) {
      console.error('Summary fetch error:', err); // Debug log
      setError(err instanceof Error ? err.message : 'Failed to fetch latency summary');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Set up auto-refresh only if refreshInterval > 0
    if (refreshInterval > 0) {
      const interval = setInterval(fetchData, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [source, hoursBack, refreshInterval]);

  return { data, loading, error, refetch: fetchData };
};

export const useLatencyMeasurements = (
  endpoint: string, 
  userId?: string, 
  options: UseLatencyDataOptions & { limit?: number } = {}
) => {
  const [data, setData] = useState<LatencyMeasurementsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { hoursBack = 1, limit = 100 } = options;

  const fetchData = async () => {
    try {
      setError(null);
      const params = new URLSearchParams({
        hours_back: hoursBack.toString(),
        limit: limit.toString(),
        ...(userId && { user_id: userId }),
      });

      const response = await fetch(`${API_BASE}/latency/measurements/${endpoint}?${params}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result: LatencyMeasurementsResponse = await response.json();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch latency measurements');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [endpoint, userId, hoursBack, limit]);

  return { data, loading, error, refetch: fetchData };
};
