import { useBudgetRefresh } from './useBudgetRefresh';

/**
 * Custom hook that wraps API calls and automatically refreshes budget on success
 * 
 * This hook provides a way to automatically update budget information
 * after successful API calls without coupling the logic to specific components.
 * 
 * Usage:
 * ```tsx
 * const { callWithBudgetRefresh } = useApiWithBudgetRefresh();
 * 
 * // Wrap your API call
 * const handleChatSubmit = async (message: string) => {
 *   await callWithBudgetRefresh(async () => {
 *     return await fetch('/api/enhanced-chat', {
 *       method: 'POST',
 *       body: JSON.stringify({ message }),
 *     });
 *   });
 * };
 * ```
 */
export const useApiWithBudgetRefresh = () => {
  const { refreshBudgetSilently } = useBudgetRefresh();

  /**
   * Wraps an API call and refreshes budget on success
   * @param apiCall - The API call function to execute
   * @param shouldRefreshBudget - Whether to refresh budget on success (default: true)
   * @returns The result of the API call
   */
  const callWithBudgetRefresh = async <T>(
    apiCall: () => Promise<T>,
    shouldRefreshBudget: boolean = true
  ): Promise<T> => {
    try {
      const result = await apiCall();
      
      // If the API call was successful and we should refresh budget
      if (shouldRefreshBudget) {
        // Refresh budget silently in the background
        refreshBudgetSilently().catch(error => {
          console.error('Background budget refresh failed:', error);
        });
      }
      
      return result;
    } catch (error) {
      // Don't refresh budget on API call failure
      throw error;
    }
  };

  /**
   * Wraps an API call specifically for enhanced chat
   * This automatically refreshes budget after successful chat interactions
   */
  const callChatWithBudgetRefresh = async (
    chatApiCall: () => Promise<any>
  ): Promise<any> => {
    return callWithBudgetRefresh(chatApiCall, true);
  };

  return {
    callWithBudgetRefresh,
    callChatWithBudgetRefresh,
  };
};
