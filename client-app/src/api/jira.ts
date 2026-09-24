import { apiClient } from './client';
import type {
  JiraConnection,
  JiraLinkResponse,
  JiraOAuthStartResponse,
  JiraProjectSummary,
  JiraSyncResponse
} from './types';

export async function startOAuth(): Promise<JiraOAuthStartResponse> {
  const { data } = await apiClient.get<JiraOAuthStartResponse>('/organizations/me/jira/oauth/start');
  return data;
}

export async function getConnection(): Promise<JiraConnection> {
  const { data } = await apiClient.get<JiraConnection>('/organizations/me/jira/connection');
  return data;
}

export async function disconnect(): Promise<void> {
  await apiClient.delete('/organizations/me/jira/connection');
}

export async function selectCloud(cloudId: string): Promise<JiraConnection> {
  const { data } = await apiClient.put<JiraConnection>('/organizations/me/jira/cloud', {
    cloud_id: cloudId
  });
  return data;
}

export async function listJiraProjects(projectId: string): Promise<JiraProjectSummary[]> {
  const { data } = await apiClient.get<JiraProjectSummary[]>('/integrations/jira/projects', {
    params: { project_id: projectId }
  });
  return data;
}

export async function linkProject(
  projectId: string,
  jiraProjectKey: string | null
): Promise<JiraLinkResponse> {
  const { data } = await apiClient.put<JiraLinkResponse>(`/projects/${projectId}/jira`, {
    jira_project_key: jiraProjectKey
  });
  return data;
}

export async function syncProject(projectId: string): Promise<JiraSyncResponse> {
  const { data } = await apiClient.post<JiraSyncResponse>(`/projects/${projectId}/jira/sync`);
  return data;
}
