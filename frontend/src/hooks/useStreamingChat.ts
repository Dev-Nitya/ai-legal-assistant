import { useState, useCallback, useRef } from 'react';

interface StreamingMessage {
  type: 'status' | 'token' | 'complete' | 'error';
  content?: string;
  message?: string;
  data?: any;
  timestamp: number;
}

interface StreamingState {
  isStreaming: boolean;
  currentResponse: string;
  status: string;
  error: string | null;
  finalData: any | null;
}

export const useStreamingChat = () => {
  const [state, setState] = useState<StreamingState>({
    isStreaming: false,
    currentResponse: '',
    status: '',
    error: null,
    finalData: null,
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  // Helper function to get auth token
  const getAuthToken = (): string | null => {
    return localStorage.getItem('auth_token');
  };

  const sendStreamingMessage = useCallback(async (
    question: string,
    complexityLevel: string = 'intermediate',
    userId?: string
  ) => {
    // Reset state
    setState({
      isStreaming: true,
      currentResponse: '',
      status: 'Connecting...',
      error: null,
      finalData: null,
    });

    try {
      // Close any existing connection
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      // Prepare request payload
      const payload = {
        question,
        complexity_level: complexityLevel,
        user_id: userId || 'anonymous',
        request_id: `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      };

      // Prepare request headers
      const token = getAuthToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // For SSE, we need to send the data via URL params or use a different approach
      // Since we need to POST data, we'll use fetch with streaming but handle SSE format
      const response = await fetch('/api/enhanced-chat-stream', {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Handle the streaming response with proper SSE parsing
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        throw new Error('Failed to get response reader');
      }

      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          setState(prev => ({
            ...prev,
            isStreaming: false,
            status: 'Complete'
          }));
          break;
        }

        // Decode the chunk and add to buffer
        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Process complete lines (SSE events end with \n\n)
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.trim() === '') continue;
          
          // Parse SSE format: "data: {...}"
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            
            if (data === '[DONE]') {
              setState(prev => ({
                ...prev,
                isStreaming: false,
                status: 'Complete'
              }));
              return;
            }

            try {
              const message: StreamingMessage = JSON.parse(data);
              
              setState(prev => {
                switch (message.type) {
                  case 'status':
                    return {
                      ...prev,
                      status: message.message || 'Processing...'
                    };
                  
                  case 'token':
                    return {
                      ...prev,
                      currentResponse: prev.currentResponse + (message.content || ''),
                      status: 'Generating response...'
                    };
                  
                  case 'complete':
                    return {
                      ...prev,
                      finalData: message.data,
                      currentResponse: message.data?.answer || prev.currentResponse,
                      status: 'Complete',
                      isStreaming: false
                    };
                  
                  case 'error':
                    return {
                      ...prev,
                      error: message.message || 'An error occurred',
                      status: 'Error',
                      isStreaming: false
                    };
                  
                  default:
                    return prev;
                }
              });
            } catch (parseError) {
              console.warn('Failed to parse streaming message:', data);
            }
          }
        }
      }

    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Connection failed',
        status: 'Error',
        isStreaming: false,
      }));
    }
  }, []);

  const stopStreaming = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setState(prev => ({
      ...prev,
      isStreaming: false,
      status: 'Stopped'
    }));
  }, []);

  return {
    ...state,
    sendStreamingMessage,
    stopStreaming,
  };
};
