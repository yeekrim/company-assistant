import axios from 'axios';
import { useAuthStore } from '../store/authStore';
import type { LoginRequest, LoginResponse } from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(err);
  }
);

const DEV_ACCOUNTS: Record<string, { password: string; name: string; role: 'admin' | 'employee'; company_id: number }> = {
  '018100001@virtual.co.kr': { password: 'pass1234', name: '김민준', role: 'admin',    company_id: 1 },
  '018100002@virtual.co.kr': { password: 'pass1234', name: '이서연', role: 'employee', company_id: 1 },
  '1021000001@repo.com':     { password: 'pass1234', name: '한소희', role: 'admin',    company_id: 2 },
  '1021000002@repo.com':     { password: 'pass1234', name: '오태양', role: 'employee', company_id: 2 },
};

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    if (import.meta.env.DEV) {
      const account = DEV_ACCOUNTS[data.email];
      if (account && account.password === data.password) {
        return {
          access_token: 'dev-token',
          token_type: 'bearer',
          user: { id: '1', email: data.email, name: account.name, role: account.role, company_id: account.company_id },
        };
      }
      throw { response: { status: 401 } };
    }
    return api.post<LoginResponse>('/api/auth/login', data).then((r) => r.data);
  },
};

export const chatApi = {
  sendMessage: async (message: string, conversationId?: string) => {
    if (import.meta.env.DEV) {
      await new Promise((r) => setTimeout(r, 800));
      return {
        id: Date.now().toString(),
        role: 'assistant' as const,
        content: `(개발 목 응답) "${message}"에 대한 답변입니다. 백엔드 RAG 파이프라인 연동 후 실제 응답이 표시됩니다.`,
        created_at: new Date().toISOString(),
        conversation_id: conversationId ?? '1',
      };
    }
    return api.post('/api/chat', { message, conversation_id: conversationId }).then((r) => r.data);
  },
};

export default api;
