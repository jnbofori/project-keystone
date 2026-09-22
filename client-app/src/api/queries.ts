import { apiClient } from './client';
import type { Query, QueryCreate } from './types';

export async function askQuestion(projectId: string, payload: QueryCreate): Promise<Query> {
  const { data } = await apiClient.post<Query>(`/projects/${projectId}/queries`, payload);
  return data;
}

export async function listQueries(projectId: string): Promise<Query[]> {
  const { data } = await apiClient.get<Query[]>(`/projects/${projectId}/queries`);
  return data;
}
