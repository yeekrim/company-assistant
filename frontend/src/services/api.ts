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

const DEV_ACCOUNTS: Record<string, { password: string; name: string }> = {
  madcoder: { password: 'root123', name: '개발자' },
};

export const authApi = {
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    if (import.meta.env.DEV) {
      const account = DEV_ACCOUNTS[data.email];
      if (account && account.password === data.password) {
        return {
          access_token: 'dev-token',
          token_type: 'bearer',
          user: { id: '1', email: data.email, name: account.name },
        };
      }
      throw { response: { status: 401 } };
    }
    return api.post<LoginResponse>('/api/auth/login', data).then((r) => r.data);
  },
};

export default api;
