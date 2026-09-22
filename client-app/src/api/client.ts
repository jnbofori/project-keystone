import axios, { type AxiosError } from 'axios';

const TOKEN_KEY = 'pka_token';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  headers: {
    Accept: 'application/json'
  }
});

apiClient.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string | Array<{ msg?: string; loc?: string[] }> }>) => {
    const status = error.response?.status ?? 0;
    const detail = error.response?.data?.detail;

    if (typeof detail === 'string') {
      throw new ApiError(detail, status);
    }

    if (Array.isArray(detail)) {
      const message = detail
        .map((item) => item.msg || JSON.stringify(item))
        .filter(Boolean)
        .join(', ');
      throw new ApiError(message || 'Validation error', status);
    }

    throw new ApiError(error.message || 'Request failed', status);
  }
);
