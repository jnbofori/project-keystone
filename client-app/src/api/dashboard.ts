import { apiClient } from './client';
import type { ProjectDashboard, SprintInsights } from './types';

export async function getProjectDashboard(projectId: string): Promise<ProjectDashboard> {
  const { data } = await apiClient.get<ProjectDashboard>(`/projects/${projectId}/dashboard`);
  return data;
}

export async function getSprintInsights(projectId: string): Promise<SprintInsights> {
  const { data } = await apiClient.post<SprintInsights>(`/projects/${projectId}/dashboard/insights`);
  return data;
}
