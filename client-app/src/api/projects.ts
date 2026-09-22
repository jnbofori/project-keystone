import { apiClient } from './client';
import type { Project, ProjectCreate, ProjectMember, ProjectMemberCreate } from './types';

export async function listProjects(): Promise<Project[]> {
  const { data } = await apiClient.get<Project[]>('/projects');
  return data;
}

export async function getProject(projectId: string): Promise<Project> {
  const { data } = await apiClient.get<Project>(`/projects/${projectId}`);
  return data;
}

export async function createProject(payload: ProjectCreate): Promise<Project> {
  const { data } = await apiClient.post<Project>('/projects', payload);
  return data;
}

export async function listMembers(projectId: string): Promise<ProjectMember[]> {
  const { data } = await apiClient.get<ProjectMember[]>(`/projects/${projectId}/members`);
  return data;
}

export async function addMember(projectId: string, payload: ProjectMemberCreate): Promise<ProjectMember> {
  const { data } = await apiClient.post<ProjectMember>(`/projects/${projectId}/members`, payload);
  return data;
}

export async function removeMember(projectId: string, userId: string): Promise<void> {
  await apiClient.delete(`/projects/${projectId}/members/${userId}`);
}
