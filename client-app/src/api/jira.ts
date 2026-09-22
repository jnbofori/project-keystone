import { apiClient } from './client';
import type {
  JiraConnection,
  JiraLinkResponse,
  JiraOAuthStartResponse,
  JiraProjectSummary,
  JiraSyncResponse
} from './types';

export async function startOAuth(projectId: string): Promise<JiraOAuthStartResponse> {
  const { data } = await apiClient.get<JiraOAuthStartResponse>(`/projects/${projectId}/jira/oauth/start`);
  return data;
}

export async function getConnection(projectId: string): Promise<JiraConnection> {
  const { data } = await apiClient.get<JiraConnection>(`/projects/${projectId}/jira/connection`);
  return data;
}

export async function disconnect(projectId: string): Promise<void> {
  await apiClient.delete(`/projects/${projectId}/jira/connection`);
}

export async function selectCloud(projectId: string, cloudId: string): Promise<JiraConnection> {
  const { data } = await apiClient.put<JiraConnection>(`/projects/${projectId}/jira/cloud`, {
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
