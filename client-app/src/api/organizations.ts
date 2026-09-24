import { apiClient } from './client';
import type { Organization, OrganizationMember, OrganizationMemberRoleUpdate, OrganizationRole } from './types';

export async function getMe(): Promise<Organization> {
  const { data } = await apiClient.get<Organization>('/organizations/me');
  return data;
}

export async function listMembers(): Promise<OrganizationMember[]> {
  const { data } = await apiClient.get<OrganizationMember[]>('/organizations/me/members');
  return data;
}

export async function rotateInviteCode(): Promise<Organization> {
  const { data } = await apiClient.post<Organization>('/organizations/me/invite-code/rotate');
  return data;
}

export async function updateMemberRole(
  userId: string,
  role: OrganizationRole
): Promise<OrganizationMember> {
  const payload: OrganizationMemberRoleUpdate = { role };
  const { data } = await apiClient.patch<OrganizationMember>(
    `/organizations/me/members/${userId}`,
    payload
  );
  return data;
}
