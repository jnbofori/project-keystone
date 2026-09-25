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

export interface DashboardSprint {
  id: string;
  name: string;
  status: string;
  starts_at: string | null;
  ends_at: string | null;
  is_fallback: boolean;
}

export interface DashboardProgress {
  percent: number | null;
  completed_points: number;
  total_points: number;
  completed_count: number;
  total_count: number;
  uses_points: boolean;
}

export interface DashboardTime {
  elapsed_percent: number | null;
  days_remaining: number | null;
}

export interface DashboardVelocity {
  last_sprint_points: number | null;
  avg_3_sprint: number | null;
  forecast_current: number | null;
}

export interface DashboardRisks {
  blocked_count: number;
  stale_blocked_count: number;
  scope_added_points: number;
  reopened_count: number;
  reopen_rate: number | null;
  pace_gap: number | null;
  carryover_likely: boolean;
  pace_label: string | null;
}

export interface DeliveryRiskIndicator {
  level: string | null;
  historical_velocity: number | null;
  required_velocity: number | null;
  velocity_ratio: number | null;
  remaining_points: number;
}

export interface ScopeRiskIndicator {
  level: string | null;
  baseline_points: number;
  current_points: number;
  scope_added_points: number;
  scope_growth_percent: number | null;
}

export interface DependencyRiskExample {
  task: string;
  blocked_by: string;
  reason: string;
}

export interface DependencyRiskIndicator {
  level: string | null;
  at_risk_count: number;
  open_dependency_count: number;
  examples: DependencyRiskExample[];
  unavailable_reason?: string | null;
}

export interface DashboardRiskIndicators {
  delivery: DeliveryRiskIndicator;
  scope: ScopeRiskIndicator;
  dependency: DependencyRiskIndicator;
}

export interface DashboardStatusCount {
  status: string;
  count: number;
}

export interface DashboardAgingItem {
  id: string;
  title: string;
  days: number;
  status: string;
  entity_type: string;
}

export interface DashboardDueItem {
  id: string;
  title: string;
  due_date: string;
  status: string;
}

export interface DashboardFlow {
  by_status: DashboardStatusCount[];
  aging_wip: DashboardAgingItem[];
  due_soon: DashboardDueItem[];
}

export interface DashboardAssigneeLoad {
  assignee_id: string | null;
  name: string;
  open_points: number;
  open_tasks: number;
  capacity_points: number | null;
}

export interface DashboardLoad {
  by_assignee: DashboardAssigneeLoad[];
}

export interface DashboardEpicHealth {
  id: string;
  title: string;
  done_stories: number;
  total_stories: number;
  percent_done: number | null;
}

export interface ProjectDashboard {
  project_id: string;
  active_sprint: DashboardSprint | null;
  progress: DashboardProgress;
  time: DashboardTime;
  velocity: DashboardVelocity;
  risks: DashboardRisks;
  risk_indicators: DashboardRiskIndicators;
  flow: DashboardFlow;
  load: DashboardLoad;
  epic_health: DashboardEpicHealth[];
  message: string | null;
}

export interface SprintInsights {
  insight: string;
  sprint_name: string | null;
  generated_at: string;
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
