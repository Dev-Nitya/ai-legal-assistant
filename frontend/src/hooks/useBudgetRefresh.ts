import { useAuth } from './useAuth';
import { useToast } from '../components/Toast';

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

  /**
   * Refresh user budget information
   * This calls the profile endpoint to get updated spending data
   */
  const refreshBudget = async (): Promise<void> => {
    try {
      await refreshProfile();
    } catch (error) {
      console.error('Budget refresh failed:', error);
      toast.error('Failed to update budget information');
    }
  };

  /**
   * Refresh budget with a success message
   * Use this when you want to show confirmation that budget was updated
   */
  const refreshBudgetWithFeedback = async (): Promise<void> => {
    try {
      await refreshProfile();
      toast.success('Budget information updated');
    } catch (error) {
      console.error('Budget refresh failed:', error);
      toast.error('Failed to update budget information');
    }
  };

  /**
   * Silent budget refresh (no toast notifications)
   * Use this for background updates where you don't want to notify the user
   */
  const refreshBudgetSilently = async (): Promise<void> => {
    try {
      // Create a temporary AuthContext-like object without toast notifications
      const response = await fetch('http://localhost:8000/api/auth/profile', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        // Update user data in localStorage (the AuthContext will pick this up)
        localStorage.setItem('user_data', JSON.stringify(userData));
        
        // Trigger a profile refresh to update the context
        await refreshProfile();
      }
    } catch (error) {
      console.error('Silent budget refresh failed:', error);
      // Don't show toast for silent refresh
    }
  };

  return {
    refreshBudget,
    refreshBudgetWithFeedback,
    refreshBudgetSilently,
  };
};
