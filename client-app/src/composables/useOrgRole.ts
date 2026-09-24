import type { OrganizationRole } from '@/api/types';
import { ORG_ROLE_RANK } from '@/api/types';

export function useOrgRole(role: OrganizationRole | null | undefined) {
  const rank = role ? ORG_ROLE_RANK[role] : -1;

  return {
    canManageOrg: rank >= ORG_ROLE_RANK.admin,
    canConnectJira: rank >= ORG_ROLE_RANK.admin,
    canRotateInvite: rank >= ORG_ROLE_RANK.admin,
    canChangeMemberRoles: rank >= ORG_ROLE_RANK.admin,
    isOwner: role === 'owner'
  };
}
