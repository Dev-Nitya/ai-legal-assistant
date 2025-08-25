import { useState } from 'react';
import type { ChatRequest, ChatResponse } from '../types';

const API_BASE_URL = 'http://localhost:8000/api';

export const useChatAPI = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = async (question: string): Promise<ChatResponse> => {
    console.log('Sending question to enhanced chat API:', question);
    setIsLoading(true);
    setError(null);

    try {
      const request: ChatRequest = {
        question,
        session_id: 'user-session-' + Date.now(),
        use_tools: true,
        complexity_level: 'simple',
        use_hybrid_search: true,
      };

      console.log('Request payload:', request);

      const response = await fetch(`${API_BASE_URL}/enhanced-chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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
      
      let data: ChatResponse;
      try {
        data = JSON.parse(responseText);
        console.log('Parsed response data:', data);
      } catch (parseError) {
        console.error('JSON parse error:', parseError);
        throw new Error('Invalid JSON response from server');
      }

      return data;
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
