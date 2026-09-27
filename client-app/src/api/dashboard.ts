import { apiClient } from './client';
import type { ProjectDashboard, ProjectDeliveryForecast, SprintInsights } from './types';

export async function getProjectDashboard(projectId: string): Promise<ProjectDashboard> {
  const { data } = await apiClient.get<ProjectDashboard>(`/projects/${projectId}/dashboard`);
  return data;
}

export async function getSprintInsights(projectId: string): Promise<SprintInsights> {
  const { data } = await apiClient.post<SprintInsights>(`/projects/${projectId}/dashboard/insights`);
  return data;
}

export async function getDeliveryForecast(projectId: string): Promise<ProjectDeliveryForecast> {
  const { data } = await apiClient.get<ProjectDeliveryForecast>(
    `/projects/${projectId}/delivery-forecast`
  );
  return data;
}
