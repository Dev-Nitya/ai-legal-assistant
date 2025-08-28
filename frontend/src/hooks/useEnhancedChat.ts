import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import type { 
  EnhancedChatRequest, 
  EnhancedChatResponse, 
  Message
} from '../types';

interface UseEnhancedChatProps {
  onMessage: (message: Message) => void;
  onError: (error: string) => void;
}

interface UseEnhancedChatReturn {
  sendMessage: (request: EnhancedChatRequest) => Promise<void>;
  isLoading: boolean;
  error: string | null;
}

const getAuthToken = (): string | null => {
  return localStorage.getItem('auth_token');
};

const enhancedChatAPI = async (request: EnhancedChatRequest): Promise<EnhancedChatResponse> => {
  const token = getAuthToken();
  
  if (!token) {
    throw new Error('Authentication required');
  }

  const response = await fetch('/api/enhanced-chat', {
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

  return response.json();
};

export const useEnhancedChat = ({ onMessage, onError }: UseEnhancedChatProps): UseEnhancedChatReturn => {
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: enhancedChatAPI,
    onSuccess: (data: EnhancedChatResponse) => {
      setError(null);
      
      // Convert API response to Message format
      const assistantMessage: Message = {
        id: Date.now().toString(),
        content: data.answer,
        sender: 'assistant',
        timestamp: new Date(),
        sources: data.source_documents,
        confidence: data.confidence,
        tools_used: data.tools_used,
        citations: data.citations,
        response_time_ms: data.response_time_ms,
        query_analysis: data.query_analysis,
        retrieval_stats: data.retrieval_stats,
      };

      onMessage(assistantMessage);
      
      // Show cost estimate if available
      if (data.cost_estimate) {
        const totalCost = Object.values(data.cost_estimate).reduce((sum, cost) => sum + cost, 0);
        if (totalCost > 0) {
          toast.success(`Query completed (Cost: $${totalCost.toFixed(4)})`);
        }
      }
    },
    onError: (error: Error) => {
      const errorMessage = error.message || 'An unexpected error occurred';
      setError(errorMessage);
      onError(errorMessage);
      toast.error(errorMessage);
    },
  });

  const sendMessage = async (request: EnhancedChatRequest): Promise<void> => {
    setError(null);
    
    try {
      await mutation.mutateAsync(request);
    } catch (error) {
      // Error handling is done in onError callback
      console.error('Enhanced chat error:', error);
    }
  };

  return {
    sendMessage,
    isLoading: mutation.isPending,
    error,
  };
};
