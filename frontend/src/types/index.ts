export interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
  sources?: string[];
  confidence?: number;
  isError?: boolean;
}

export interface ChatRequest {
  question: string;
  session_id: string;
  use_tools?: boolean;
  complexity_level?: string;
  filters?: Record<string, any>;
  use_hybrid_search?: boolean;
}

export interface ChatResponse {
  answer: string;
  source_documents: Array<{
    source: string;
    page: string | number;
    document_type: string;
    relevance_snippet: string;
    sections: string[];
    legal_topics: string[];
  }>;
  confidence: number;
  tools_used?: string[];
  citations?: Array<{
    source: string;
    type: string;
    sections: string[];
    acts: string[];
    page: string | number;
  }>;
  reading_level: string;
  response_time_ms: number;
  query_analysis: Record<string, any>;
  retrieval_stats: Record<string, any>;
}

export interface APIError {
  message: string;
  status?: number;
}
