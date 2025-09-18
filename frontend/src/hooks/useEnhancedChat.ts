import { useState } from 'react';
import toast from 'react-hot-toast';
import type { 
  EnhancedChatRequest, 
  Message
} from '../types';

const API_BASE_URL = 'http://localhost:8000/api';

interface UseEnhancedChatProps {
  onMessage: (message: Message) => void;
  onError: (error: string) => void;
  onStreamingStart?: () => void; // Callback when streaming starts
}

interface UseEnhancedChatReturn {
  sendMessage: (request: EnhancedChatRequest) => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

const getAuthToken = (): string | null => {
  return localStorage.getItem('auth_token');
};

const enhancedChatStreamAPI = async (
  request: EnhancedChatRequest,
  onMessage: (message: Message) => void,
  onStreamingStart?: () => void
): Promise<void> => {
  const token = getAuthToken();
  
  if (!token) {
    throw new Error('Authentication required');
  }

  const response = await fetch(`${API_BASE_URL}/enhanced-chat-stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.message || 'Failed to send message');
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Stream not available');
  }

  let fullResponse = '';
  let finalData: any = null;
  let currentMessageId = Date.now().toString();
  let isFirstToken = true;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = new TextDecoder().decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          
          if (data === '[DONE]') {
            // Stream complete, create final message with all metadata
            if (finalData) {
              const finalMessage: Message = {
                id: currentMessageId,
                content: fullResponse,
                sender: 'assistant',
                timestamp: new Date(),
                sources: finalData.source_documents,
                confidence: finalData.confidence,
                tools_used: finalData.tools_used,
                citations: finalData.citations,
                response_time_ms: finalData.response_time_ms,
                query_analysis: finalData.query_analysis,
                retrieval_stats: finalData.retrieval_stats,
              };
              onMessage(finalMessage);

              // Show cost estimate if available
              if (finalData.cost_estimate) {
                const totalCost = Object.values(finalData.cost_estimate).reduce((sum: number, cost: any) => sum + cost, 0);
                if (totalCost > 0) {
                  toast.success(`Query completed (Cost: $${totalCost.toFixed(4)})`);
                }
              }
            }
            return;
          }

          try {
            const eventData = JSON.parse(data);
            
            if (eventData.type === 'token') {
              // Call onStreamingStart only on the first token
              if (isFirstToken && onStreamingStart) {
                onStreamingStart();
                isFirstToken = false;
              }
              
              fullResponse += eventData.content;
              
              // Send streaming update with current content
              const streamingMessage: Message = {
                id: currentMessageId,
                content: fullResponse,
                sender: 'assistant',
                timestamp: new Date(),
                isStreaming: true, // Add a flag to indicate this is a streaming message
              };
              onMessage(streamingMessage);
              
            } else if (eventData.type === 'complete') {
              finalData = eventData.data;
              // For cached responses, the answer comes directly in the complete event
              if (eventData.data && eventData.data.answer && !fullResponse) {
                fullResponse = eventData.data.answer;
              }
            } else if (eventData.type === 'error') {
              throw new Error(eventData.error || 'Stream error occurred');
            }
          } catch (parseError) {
            if (data !== '') {
              console.warn('Failed to parse SSE data:', data);
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
};

export const useEnhancedChat = ({ onMessage, onError, onStreamingStart }: UseEnhancedChatProps): UseEnhancedChatReturn => {
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (request: EnhancedChatRequest): Promise<void> => {
    setError(null);
    setIsLoading(true);
    
    try {
      await enhancedChatStreamAPI(request, onMessage, () => {
        setIsLoading(false); // Stop loading when streaming starts
        if (onStreamingStart) {
          onStreamingStart();
        }
      });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unexpected error occurred';
      setError(errorMessage);
      onError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    sendMessage,
    isLoading,
    error,
  };
};
