<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue';
import { useRouter } from 'vue-router';
import BaseBreadcrumb from '@/components/shared/BaseBreadcrumb.vue';
import UiParentCard from '@/components/shared/UiParentCard.vue';
import ProjectFormDialog from '@/components/projects/ProjectFormDialog.vue';
import { useAuthStore } from '@/stores/auth';
import { useProjectsStore } from '@/stores/projects';
import { documentsApi } from '@/api';
import type { Document } from '@/api/types';

const router = useRouter();
const auth = useAuthStore();
const projectsStore = useProjectsStore();

const showCreateDialog = ref(false);
const allDocuments = ref<Document[]>([]);
const statsLoading = ref(false);

const page = ref({ title: 'Dashboard' });
const breadcrumbs = shallowRef([
  { title: 'Home', disabled: false, href: '/dashboard/default' },
  { title: 'Dashboard', disabled: true, href: '#' }
]);

const readyDocuments = computed(() => allDocuments.value.filter((doc) => doc.status === 'ready').length);

async function loadDashboardData() {
  statsLoading.value = true;
  try {
    await projectsStore.fetchProjects();
    const documentLists = await Promise.all(
      projectsStore.projects.map((project) => documentsApi.listDocuments(project.id).catch(() => []))
    );
    allDocuments.value = documentLists.flat();
  } finally {
    statsLoading.value = false;
  }
}

function openProject(projectId: string) {
  router.push(`/projects/${projectId}`);
}

async function handleProjectCreated(projectId: string) {
  showCreateDialog.value = false;
  await loadDashboardData();
  router.push(`/projects/${projectId}`);
}

onMounted(loadDashboardData);
</script>

<template>
  <BaseBreadcrumb :title="page.title" :breadcrumbs="breadcrumbs" />

  <v-row>
    <v-col cols="12">
      <UiParentCard title="Welcome">
        <p class="mb-0">
          Hello {{ auth.user?.email }}, manage your project knowledge base, upload documents, and ask questions grounded
          in your project context.
        </p>
      </UiParentCard>
    </v-col>

    <v-col cols="12" sm="6" md="4">
      <v-card variant="outlined">
        <v-card-text>
          <div class="text-body-small text-medium-emphasis">Projects</div>
          <div class="text-h4">{{ projectsStore.projects.length }}</div>
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="12" sm="6" md="4">
      <v-card variant="outlined">
        <v-card-text>
          <div class="text-body-small text-medium-emphasis">Documents</div>
          <div class="text-h4">{{ allDocuments.length }}</div>
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="12" sm="6" md="4">
      <v-card variant="outlined">
        <v-card-text>
          <div class="text-body-small text-medium-emphasis">Ready for Q&amp;A</div>
          <div class="text-h4">{{ readyDocuments }}</div>
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="12">
      <UiParentCard title="Recent Projects">
        <template #action>
          <v-btn color="primary" variant="flat" @click="showCreateDialog = true">Create Project</v-btn>
        </template>

        <v-progress-linear v-if="statsLoading || projectsStore.loading" indeterminate color="primary" class="mb-4" />

        <v-alert v-if="!statsLoading && projectsStore.projects.length === 0" type="info" variant="tonal">
          No projects yet. Create your first project to start uploading documents.
        </v-alert>

        <v-table v-else density="comfortable">
          <thead>
            <tr>
              <th>Name</th>
              <th class="d-none d-md-table-cell">Description</th>
              <th>Role</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="project in projectsStore.projects.slice(0, 5)" :key="project.id">
              <td>{{ project.name }}</td>
              <td class="d-none d-md-table-cell text-medium-emphasis">
                {{ project.description || '—' }}
              </td>
              <td>
                <v-chip size="small" color="primary" variant="tonal">{{ project.current_user_role }}</v-chip>
              </td>
              <td class="text-right">
                <v-btn size="small" variant="text" color="primary" @click="openProject(project.id)">Open</v-btn>
              </td>
            </tr>
          </tbody>
        </v-table>
      </UiParentCard>
    </v-col>
  </v-row>

  <ProjectFormDialog v-model="showCreateDialog" @created="handleProjectCreated" />
</template>
