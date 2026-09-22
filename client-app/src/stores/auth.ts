import { defineStore } from 'pinia';
import { authApi } from '@/api';
import { getStoredToken, setStoredToken } from '@/api/client';
import type { User } from '@/api/types';
import { getErrorMessage } from '@/utils/apiError';

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as User | null,
    token: getStoredToken(),
    loading: false
  }),

  getters: {
    isAuthenticated: (state) => !!state.token && !!state.user
  },

  actions: {
    async login(email: string, password: string) {
      this.loading = true;
      try {
        const tokenResponse = await authApi.login(email, password);
        this.token = tokenResponse.access_token;
        setStoredToken(this.token);
        await this.fetchMe();
      } finally {
        this.loading = false;
      }
    },

    async register(email: string, password: string) {
      this.loading = true;
      try {
        await authApi.register({ email, password });
        await this.login(email, password);
      } finally {
        this.loading = false;
      }
    },

    async fetchMe() {
      if (!this.token) {
        this.user = null;
        return;
      }

      this.loading = true;
      try {
        this.user = await authApi.getMe();
      } catch (error) {
        this.logout();
        throw new Error(getErrorMessage(error, 'Failed to load user'));
      } finally {
        this.loading = false;
      }
    },

    logout() {
      this.user = null;
      this.token = null;
      setStoredToken(null);
    }
  }
});
