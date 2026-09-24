import { defineStore } from 'pinia';
import { organizationsApi } from '@/api';
import type { Organization, OrganizationMember, OrganizationRole } from '@/api/types';

export const useOrganizationStore = defineStore('organization', {
  state: () => ({
    organization: null as Organization | null,
    members: [] as OrganizationMember[],
    loading: false,
    membersLoading: false
  }),

  getters: {
    currentRole: (state) => state.organization?.current_user_role ?? null
  },

  actions: {
    async fetchMe() {
      this.loading = true;
      try {
        this.organization = await organizationsApi.getMe();
        return this.organization;
      } finally {
        this.loading = false;
      }
    },

    async fetchMembers() {
      this.membersLoading = true;
      try {
        this.members = await organizationsApi.listMembers();
        return this.members;
      } finally {
        this.membersLoading = false;
      }
    },

    async rotateInviteCode() {
      this.organization = await organizationsApi.rotateInviteCode();
      return this.organization;
    },

    async updateMemberRole(userId: string, role: OrganizationRole) {
      const updated = await organizationsApi.updateMemberRole(userId, role);
      const index = this.members.findIndex((member) => member.user_id === userId);
      if (index >= 0) {
        this.members[index] = updated;
      }
      return updated;
    },

    clear() {
      this.organization = null;
      this.members = [];
    }
  }
});
