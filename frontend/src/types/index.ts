export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'employee';
  company_id: number;
  company_name: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface SourceChunk {
  source: string;
  effective_date: string; // YYYY-MM-DD 또는 '미상'
  text: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  sources?: SourceChunk[]; // assistant 답변의 근거 청크
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
}
