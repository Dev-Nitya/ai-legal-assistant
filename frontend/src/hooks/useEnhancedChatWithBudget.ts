import { useEnhancedChat } from './useEnhancedChat';
import { useBudgetRefresh } from './useBudgetRefresh';
import type { EnhancedChatRequest, Message } from '../types';

interface UseEnhancedChatWithBudgetProps {
  onMessage: (message: Message) => void;
  onError: (error: string) => void;
  onStreamingStart?: () => void;
  autoRefreshBudget?: boolean; // Whether to automatically refresh budget on successful chat
}

interface UseEnhancedChatWithBudgetReturn {
  sendMessage: (request: EnhancedChatRequest) => Promise<void>;
  isLoading: boolean;
  error: string | null;
  refreshBudget: () => Promise<void>;
}

/**
 * Enhanced chat hook with automatic budget refresh
 * 
 * This hook wraps the existing useEnhancedChat hook and adds automatic
 * budget refresh functionality after successful chat interactions.
 * 
 * Usage:
 * ```tsx
 * const { sendMessage, isLoading, error, refreshBudget } = useEnhancedChatWithBudget({
 *   onMessage: handleMessage,
 *   onError: handleError,
 *   autoRefreshBudget: true, // Default: true
 * });
 * ```
 */
export const useEnhancedChatWithBudget = ({
  onMessage,
  onError,
  onStreamingStart,
  autoRefreshBudget = true,
}: UseEnhancedChatWithBudgetProps): UseEnhancedChatWithBudgetReturn => {
  const { refreshBudgetSilently } = useBudgetRefresh();

  // Wrap the onMessage callback to include budget refresh
  const handleMessageWithBudgetRefresh = async (message: Message) => {
    // Call the original onMessage callback
    onMessage(message);

    // Only refresh budget for complete messages (not streaming updates)
    // and only for assistant messages (not user messages)
    if (
      autoRefreshBudget && 
      message.sender === 'assistant' && 
      !message.isStreaming
    ) {
      try {
        await refreshBudgetSilently();
      } catch (error) {
        console.error('Budget refresh after chat failed:', error);
        // Don't propagate this error to the user - budget refresh is secondary
      }
    }
  };

  // Use the existing enhanced chat hook with our wrapped callback
  const enhancedChat = useEnhancedChat({
    onMessage: handleMessageWithBudgetRefresh,
    onError,
    onStreamingStart,
  });

  // Expose the budget refresh function for manual calls
  const manualRefreshBudget = async (): Promise<void> => {
    try {
      await refreshBudgetSilently();
    } catch (error) {
      console.error('Manual budget refresh failed:', error);
      throw error;
    }
  };

  return {
    sendMessage: enhancedChat.sendMessage,
    isLoading: enhancedChat.isLoading,
    error: enhancedChat.error,
    refreshBudget: manualRefreshBudget,
  };
};
