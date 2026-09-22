import type { ProjectRole } from '@/api/types';
import { ROLE_RANK } from '@/api/types';

export function useProjectRole(role: ProjectRole | null | undefined) {
  const rank = role ? ROLE_RANK[role] : -1;

  return {
    canQuery: rank >= ROLE_RANK.viewer,
    canUpload: rank >= ROLE_RANK.member,
    canManageMembers: rank >= ROLE_RANK.admin,
    canManageJira: rank >= ROLE_RANK.admin,
    canDeleteDocuments: rank >= ROLE_RANK.admin,
    canViewQueryHistory: rank >= ROLE_RANK.member
  };
}
