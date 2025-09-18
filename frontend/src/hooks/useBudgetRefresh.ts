import { useAuth } from './useAuth';
import { useToast } from '../components/Toast';
import { useCallback, useRef } from 'react';

/**
 * Custom hook for managing budget updates
 * 
 * This hook provides a clean way to refresh user budget information
 * after API operations that might affect spending (like chat calls).
 * 
 * Usage:
 * ```tsx
 * const { refreshBudget, isRefreshing } = useBudgetRefresh();
 * 
 * // After a successful API call
 * await refreshBudget();
 * ```
 */
export const useBudgetRefresh = () => {
  const { refreshProfile } = useAuth();
  const toast = useToast();
  const lastRefreshRef = useRef<number>(0);
  const DEBOUNCE_MS = 2000; // Prevent multiple refreshes within 2 seconds

  /**
   * Check if enough time has passed since last refresh
   */
  const shouldRefresh = (): boolean => {
    const now = Date.now();
    const timeSinceLastRefresh = now - lastRefreshRef.current;
    return timeSinceLastRefresh >= DEBOUNCE_MS;
  };

  /**
   * Refresh user budget information
   * This calls the profile endpoint to get updated spending data
   */
  const refreshBudget = useCallback(async (): Promise<void> => {
    if (!shouldRefresh()) {
      console.log('Budget refresh skipped - too recent');
      return;
    }

    try {
      lastRefreshRef.current = Date.now();
      await refreshProfile();
    } catch (error) {
      console.error('Budget refresh failed:', error);
      toast.error('Failed to update budget information');
    }
  }, [refreshProfile, toast]);

  /**
   * Refresh budget with a success message
   * Use this when you want to show confirmation that budget was updated
   */
  const refreshBudgetWithFeedback = useCallback(async (): Promise<void> => {
    if (!shouldRefresh()) {
      console.log('Budget refresh with feedback skipped - too recent');
      return;
    }

    try {
      lastRefreshRef.current = Date.now();
      await refreshProfile();
      toast.success('Budget information updated');
    } catch (error) {
      console.error('Budget refresh failed:', error);
      toast.error('Failed to update budget information');
    }
  }, [refreshProfile, toast]);

  /**
   * Silent budget refresh (no toast notifications)
   * Use this for background updates where you don't want to notify the user
   */
  const refreshBudgetSilently = useCallback(async (): Promise<void> => {
    if (!shouldRefresh()) {
      console.log('Silent budget refresh skipped - too recent');
      return;
    }

    try {
      lastRefreshRef.current = Date.now();
      await refreshProfile();
    } catch (error) {
      console.error('Silent budget refresh failed:', error);
      // Don't show toast for silent refresh
    }
  }, [refreshProfile]);

  return {
    refreshBudget,
    refreshBudgetWithFeedback,
    refreshBudgetSilently,
  };
};
