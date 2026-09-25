import { apiClient } from './client';
import type { ProjectDashboard } from './types';

export async function getProjectDashboard(projectId: string): Promise<ProjectDashboard> {
  const { data } = await apiClient.get<ProjectDashboard>(`/projects/${projectId}/dashboard`);
  return data;
}
