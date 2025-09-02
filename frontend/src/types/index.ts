// User Authentication Types
export type UserTier = 'free' | 'basic' | 'premium' | 'enterprise';

export type ComplexityLevel = 'simple' | 'intermediate' | 'advanced';

export type DocumentType = 'case_law' | 'statute' | 'regulation' | 'constitution' | 'legal_document';

export interface BudgetInfo {
  limits: {
    daily_limit: number;
    monthly_limit: number;
    hourly_limit: number;
  };
  usage: {
    daily_spent: number;
    monthly_spent: number;
    hourly_spent: number;
  };
}

export interface User {
  user_id: string;
  email: string;
  full_name: string;
  tier: UserTier;
  is_active: boolean;
  created_at?: string;
  last_login?: string;
  budget_info?: BudgetInfo;
  budget_limits?: Record<string, number>;
}

export interface AuthRequest {
  email: string;
  password: string;
}

export interface RegisterRequest extends AuthRequest {
  full_name: string;
  tier?: UserTier;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// Chat Types
export interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant';
  timestamp: Date;
  sources?: SourceDocument[];
  confidence?: number;
  isError?: boolean;
  tools_used?: string[];
  citations?: Citation[];
  response_time_ms?: number;
  query_analysis?: QueryAnalysis;
  retrieval_stats?: RetrievalStats;
}

export interface DocumentFilters {
  document_types?: DocumentType[];
  legal_topics?: string[];
  jurisdiction?: string;
  acts?: string[];
  sections?: string[];
}

export interface EnhancedChatRequest {
  user_id?: string;
  question: string;
  complexity_level?: ComplexityLevel;
}

// Simple Chat Request for compatibility
export interface ChatRequest {
  question: string;
  user_id?: string;
  session_id?: string;
  complexity_level?: ComplexityLevel;
}

// Simple Chat Response for compatibility
export interface ChatResponse {
  answer: string;
  source_documents: string[] | SourceDocument[];
  confidence: number;
  tools_used?: string[];
  citations?: Citation[];
  reading_level?: ComplexityLevel;
}

export interface SourceDocument {
  source: string;
  page: string | number;
  document_type: DocumentType;
  relevance_snippet: string;
  sections: string[];
  legal_topics: string[];
  confidence_score?: number;
}

export interface Citation {
  source: string;
  type: string;
  sections: string[];
  acts: string[];
  page: string | number;
}

export interface QueryAnalysis {
  legal_domain?: string;
  intent?: string;
  entities: string[];
  complexity_detected?: ComplexityLevel;
  suggested_filters?: DocumentFilters;
  original_query: string;
  processed_query: string;
  sections: string[];
  acts: string[];
}

export interface RetrievalStats {
  documents_retrieved: number;
  unique_sources: number;
  average_relevance: number;
  search_time_ms?: number;
}

export interface EnhancedChatResponse {
  answer: string;
  source_documents: SourceDocument[];
  confidence: number;
  tools_used: string[];
  citations: Citation[];
  reading_level: ComplexityLevel;
  response_time_ms: number;
  query_analysis: QueryAnalysis;
  retrieval_stats: RetrievalStats;
  from_cache: boolean;
  cost_estimate?: Record<string, number>;
}

// Evaluation Types
export interface EvaluationRequest {
  question: string;
  user_id?: string;
  use_ground_truth?: boolean;
  ground_truth_answer?: string;
}

export interface BatchEvaluationRequest {
  category?: string;
  difficulty?: string;
  max_questions: number;
  user_id?: string;
}

export interface EvaluationResult {
  retrieval_precision_at_3: number;
  retrieval_precision_at_5: number;
  answer_relevance: number;
  answer_faithfulness: number;
  overall_score: number;
  retrieved_doc_count: number;
  answer_length_tokens: number;
  evaluation_timestamp: string;
}

export interface EvaluationResponse {
  question: string;
  generated_answer: string;
  evaluation_result: EvaluationResult;
  retrieved_documents_count: number;
  processing_time_seconds: number;
  timestamp: string;
}

export interface BatchEvaluationResponse {
  total_questions_tested: number;
  average_scores: Record<string, number>;
  individual_results: EvaluationResponse[];
  category_breakdown: Record<string, Record<string, number>>;
  summary: Record<string, any>;
}

// API Error Types
export interface APIError {
  message: string;
  status?: number;
  error_code?: string;
  details?: Record<string, any>;
}

export interface ValidationErrorResponse {
  error_message: string;
  details: Record<string, any>;
}

// UI State Types
export interface AppState {
  user: User | null;
  isAuthenticated: boolean;
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  chatSettings: ChatSettings;
}

export interface ChatSettings {
  complexity_level: ComplexityLevel;
}
