import { useState } from 'react';
import type { ChatRequest, ChatResponse, EnhancedChatRequest, EnhancedChatResponse } from '../types';

const API_BASE_URL = 'http://localhost:8000/api';

interface UseChatAPIOptions {
  token?: string;
  userId?: string;
}

export const useChatAPI = (options: UseChatAPIOptions = {}) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = async (question: string, useEnhanced: boolean = true): Promise<ChatResponse> => {
    console.log('Sending question to API:', question);
    setIsLoading(true);
    setError(null);

    try {
      const endpoint = useEnhanced ? '/enhanced-chat' : '/chat';
      
      const request: EnhancedChatRequest | ChatRequest = useEnhanced ? {
        question,
        user_id: options.userId || 'anonymous',
        complexity_level: 'simple',
        use_tools: true,
        use_hybrid_search: true,
        bypass_cache: false,
        include_citations: true,
        max_sources: 5,
      } : {
        question,
        user_id: options.userId || 'anonymous',
        session_id: 'user-session-' + Date.now(),
        use_tools: true,
        complexity_level: 'simple',
      };

      console.log('Request payload:', request);

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      if (options.token) {
        headers['Authorization'] = `Bearer ${options.token}`;
      }

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(request),
      });

      console.log('Response status:', response.status);
      console.log('Response headers:', Object.fromEntries(response.headers.entries()));

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response text:', errorText);
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          errorData = { detail: errorText };
        }
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      const responseText = await response.text();
      console.log('Raw response text:', responseText);
      
      let data: ChatResponse | EnhancedChatResponse;
      try {
        data = JSON.parse(responseText);
        console.log('Parsed response data:', data);
      } catch (parseError) {
        console.error('JSON parse error:', parseError);
        throw new Error('Invalid JSON response from server');
      }

      // Normalize response format for consistency
      const normalizedResponse: ChatResponse = {
        answer: data.answer,
        source_documents: data.source_documents,
        confidence: data.confidence,
        tools_used: data.tools_used,
        citations: (data as EnhancedChatResponse).citations,
        reading_level: (data as EnhancedChatResponse).reading_level,
      };

      return normalizedResponse;
    } catch (err) {
      console.error('API call error:', err);
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
      setError(errorMessage);
      throw err;
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
