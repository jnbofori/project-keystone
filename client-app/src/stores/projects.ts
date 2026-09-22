import { defineStore } from 'pinia';
import { documentsApi, projectsApi } from '@/api';
import type { Document, Project, ProjectMember, ProjectMemberCreate, ProjectCreate } from '@/api/types';

export const useProjectsStore = defineStore('projects', {
  state: () => ({
    projects: [] as Project[],
    currentProject: null as Project | null,
    members: [] as ProjectMember[],
    documents: [] as Document[],
    loading: false
  }),

  actions: {
    async fetchProjects() {
      this.loading = true;
      try {
        this.projects = await projectsApi.listProjects();
      } finally {
        this.loading = false;
      }
    },

    async fetchProject(projectId: string) {
      this.loading = true;
      try {
        this.currentProject = await projectsApi.getProject(projectId);
      } finally {
        this.loading = false;
      }
    },

    async createProject(payload: ProjectCreate) {
      const project = await projectsApi.createProject(payload);
      this.projects.unshift(project);
      return project;
    },

    async fetchMembers(projectId: string) {
      this.members = await projectsApi.listMembers(projectId);
    },

    async addMember(projectId: string, payload: ProjectMemberCreate) {
      const member = await projectsApi.addMember(projectId, payload);
      this.members.push(member);
      return member;
    },

    async removeMember(projectId: string, userId: string) {
      await projectsApi.removeMember(projectId, userId);
      this.members = this.members.filter((member) => member.user_id !== userId);
    },

    async fetchDocuments(projectId: string) {
      this.documents = await documentsApi.listDocuments(projectId);
    }
  }
});
