import { apiClient } from './client';
import type {
  GithubActivityResponse,
  GithubInstallation,
  GithubInstallStartResponse,
  GithubLinkedRepo,
  GithubRepoSummary,
  GithubSyncResponse
} from './types';

export async function startInstall(): Promise<GithubInstallStartResponse> {
  const { data } = await apiClient.get<GithubInstallStartResponse>('/organizations/me/github/install/start');
  return data;
}

export async function listInstallations(): Promise<GithubInstallation[]> {
  const { data } = await apiClient.get<GithubInstallation[]>('/organizations/me/github/installations');
  return data;
}

export async function removeInstallation(installationId: string): Promise<void> {
  await apiClient.delete(`/organizations/me/github/installations/${installationId}`);
}

export async function listAvailableRepos(projectId: string): Promise<GithubRepoSummary[]> {
  const { data } = await apiClient.get<GithubRepoSummary[]>('/integrations/github/repos', {
    params: { project_id: projectId }
  });
  return data;
}

export async function getLinkedRepos(projectId: string): Promise<GithubLinkedRepo[]> {
  const { data } = await apiClient.get<GithubLinkedRepo[]>(`/projects/${projectId}/github/repos`);
  return data;
}

export async function setLinkedRepos(projectId: string, repoIds: number[]): Promise<GithubLinkedRepo[]> {
  const { data } = await apiClient.put<GithubLinkedRepo[]>(`/projects/${projectId}/github/repos`, {
    repo_ids: repoIds
  });
  return data;
}

export async function syncProject(projectId: string): Promise<GithubSyncResponse> {
  const { data } = await apiClient.post<GithubSyncResponse>(`/projects/${projectId}/github/sync`);
  return data;
}

export async function getActivity(projectId: string, limit = 20): Promise<GithubActivityResponse> {
  const { data } = await apiClient.get<GithubActivityResponse>(`/projects/${projectId}/github/activity`, {
    params: { limit }
  });
  return data;
}
