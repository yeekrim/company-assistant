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
  ): Promise<{ id: string; content: string; created_at: string }> => {
    const res = await api.post('/api/chat', { message: query, conversation_id: conversationId ?? null });
    return res.data;
  },
};

export const documentApi = {
  upload: async (file: File): Promise<{ message: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post('/api/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
};

export default api;
