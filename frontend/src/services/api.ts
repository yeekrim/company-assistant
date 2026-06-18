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

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    return api.post<LoginResponse>('/api/auth/login', data).then((r) => r.data);
  },
};

export const chatApi = {
  sendMessage: async (
    query: string,
    conversationId?: string
  ): Promise<{ id: string; content: string; created_at: string; conversation_id: string }> => {
    const res = await api.post('/api/chat', { message: query, conversation_id: conversationId ? Number(conversationId) : null });
    return res.data;
  },

  listConversations: async (): Promise<{ id: string; title: string; created_at: string }[]> => {
    const res = await api.get('/api/chat/conversations');
    return res.data;
  },

  getMessages: async (conversationId: string): Promise<{ id: string; role: string; content: string; created_at: string }[]> => {
    const res = await api.get(`/api/chat/conversations/${conversationId}/messages`);
    return res.data;
  },

  deleteConversation: async (conversationId: string): Promise<void> => {
    await api.delete(`/api/chat/conversations/${conversationId}`);
  },
};

export const documentApi = {
  upload: async (files: File[]): Promise<{ uploaded: { file: string }[]; errors: { file: string; error: string }[] }> => {
    const formData = new FormData();
    files.forEach((f) => formData.append('files', f));
    const res = await api.post('/api/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  list: async (): Promise<{ name: string; chunks: number }[]> => {
    const res = await api.get('/api/documents');
    return res.data.documents;
  },

  delete: async (docName: string): Promise<void> => {
    await api.delete(`/api/documents/${encodeURIComponent(docName)}`);
  },
};

export default api;
