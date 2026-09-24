export type ProjectRole = 'owner' | 'admin' | 'member' | 'viewer';

export type OrganizationRole = 'owner' | 'admin' | 'member';

export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed';

export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

export interface UserRegister {
  email: string;
  password: string;
  organization_name?: string;
  invite_code?: string;
}

export interface Organization {
  id: string;
  name: string;
  invite_code: string | null;
  created_by: string;
  created_at: string;
  current_user_role: OrganizationRole;
}

export interface OrganizationMember {
  id: string;
  user_id: string;
  email: string;
  role: OrganizationRole;
  created_at: string;
}

export interface OrganizationMemberRoleUpdate {
  role: OrganizationRole;
}

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  jira_project_key: string | null;
  jira_project_id: string | null;
  created_by: string;
  created_at: string;
  current_user_role: ProjectRole;
}

export interface ProjectCreate {
  name: string;
  description?: string | null;
}

export interface ProjectMember {
  id: string;
  user_id: string;
  email: string;
  role: ProjectRole;
  created_at: string;
}

export interface ProjectMemberCreate {
  email: string;
  role: ProjectRole;
}

export interface Document {
  id: string;
  project_id: string;
  filename: string;
  status: DocumentStatus;
  uploaded_by: string;
  chunk_count: number;
  error_message: string | null;
  created_at: string;
}

export interface SourceCitation {
  document_id: string | null;
  filename: string | null;
  text: string;
  score: number | null;
}

export interface Query {
  id: string;
  question: string;
  answer: string;
  sources: SourceCitation[];
  created_at: string;
}

export interface QueryCreate {
  question: string;
}

export interface JiraOAuthStartResponse {
  authorize_url: string;
}

export interface JiraCloudSite {
  cloud_id: string;
  site_url: string | null;
  site_name: string | null;
}

export interface JiraConnection {
  connected: boolean;
  cloud_id: string | null;
  site_url: string | null;
  site_name: string | null;
  token_expires_at: string | null;
  connected_by: string | null;
  needs_site_selection: boolean;
  available_sites: JiraCloudSite[];
}

export interface JiraProjectSummary {
  id: string;
  key: string;
  name: string;
  project_type_key: string | null;
}

export interface JiraLinkResponse {
  project_id: string;
  jira_project_key: string | null;
  jira_project_id: string | null;
}

export interface JiraSyncErrorItem {
  entity: string;
  key: string | null;
  message: string;
}

export interface JiraSyncResponse {
  project_id: string;
  jira_project_key: string;
  team_members: number;
  sprints: number;
  epics: number;
  stories: number;
  tasks: number;
  events: number;
  errors: JiraSyncErrorItem[];
}

export const ROLE_RANK: Record<ProjectRole, number> = {
  viewer: 0,
  member: 1,
  admin: 2,
  owner: 3
};

export const ORG_ROLE_RANK: Record<OrganizationRole, number> = {
  member: 0,
  admin: 1,
  owner: 2
};

export const SUPPORTED_EXTENSIONS = ['.txt', '.md', '.pdf', '.docx'];
