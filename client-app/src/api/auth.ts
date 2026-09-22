import { apiClient } from './client';
import type { Token, User, UserRegister } from './types';

export async function register(payload: UserRegister): Promise<User> {
  const { data } = await apiClient.post<User>('/auth/register', payload);
  return data;
}

export async function login(email: string, password: string): Promise<Token> {
  const params = new URLSearchParams();
  params.append('username', email);
  params.append('password', password);

  const { data } = await apiClient.post<Token>('/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  });
  return data;
}

export async function getMe(): Promise<User> {
  const { data } = await apiClient.get<User>('/auth/me');
  return data;
}
