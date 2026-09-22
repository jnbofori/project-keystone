<script setup lang="ts">
import { computed, onMounted, ref, shallowRef } from 'vue';
import { useRouter } from 'vue-router';
import BaseBreadcrumb from '@/components/shared/BaseBreadcrumb.vue';
import UiParentCard from '@/components/shared/UiParentCard.vue';
import ProjectFormDialog from '@/components/projects/ProjectFormDialog.vue';
import { useProjectsStore } from '@/stores/projects';

const router = useRouter();
const projectsStore = useProjectsStore();

const search = ref('');
const showCreateDialog = ref(false);

const page = ref({ title: 'Projects' });
const breadcrumbs = shallowRef([
  { title: 'Home', disabled: false, href: '/dashboard/default' },
  { title: 'Projects', disabled: true, href: '#' }
]);

const filteredProjects = computed(() => {
  const query = search.value.trim().toLowerCase();
  if (!query) return projectsStore.projects;
  return projectsStore.projects.filter(
    (project) =>
      project.name.toLowerCase().includes(query) ||
      (project.description ?? '').toLowerCase().includes(query)
  );
});

function openProject(projectId: string) {
  router.push(`/projects/${projectId}`);
}

async function handleProjectCreated(projectId: string) {
  showCreateDialog.value = false;
  router.push(`/projects/${projectId}`);
}

onMounted(() => {
  projectsStore.fetchProjects();
});
</script>

<template>
  <BaseBreadcrumb :title="page.title" :breadcrumbs="breadcrumbs" />

  <UiParentCard title="Your Projects">
    <template #action>
      <v-btn color="primary" variant="flat" @click="showCreateDialog = true">Create Project</v-btn>
    </template>

    <v-text-field
      v-model="search"
      label="Search projects"
      prepend-inner-icon="$magnify"
      hide-details="auto"
      class="mb-4"
      clearable
    />

    <v-progress-linear v-if="projectsStore.loading" indeterminate color="primary" class="mb-4" />

    <v-alert v-if="!projectsStore.loading && filteredProjects.length === 0" type="info" variant="tonal">
      No projects found. Create a project to upload documents and ask questions.
    </v-alert>

    <v-row v-else>
      <v-col v-for="project in filteredProjects" :key="project.id" cols="12" md="6" lg="4">
        <v-card variant="outlined" class="h-100">
          <v-card-title>{{ project.name }}</v-card-title>
          <v-card-text>
            <p class="text-medium-emphasis mb-3">{{ project.description || 'No description' }}</p>
            <v-chip size="small" color="primary" variant="tonal">{{ project.current_user_role }}</v-chip>
          </v-card-text>
          <v-card-actions>
            <v-btn color="primary" variant="text" @click="openProject(project.id)">Open</v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <v-data-table
      v-if="filteredProjects.length"
      class="d-none d-lg-block mt-6"
      :headers="[
        { title: 'Name', key: 'name' },
        { title: 'Description', key: 'description' },
        { title: 'Role', key: 'current_user_role' },
        { title: 'Created', key: 'created_at' },
        { title: 'Actions', key: 'actions', sortable: false, align: 'end' }
      ]"
      :items="filteredProjects"
      item-value="id"
      density="comfortable"
    >
      <template #item.description="{ item }">
        {{ item.description || '—' }}
      </template>
      <template #item.current_user_role="{ item }">
        <v-chip size="small" color="primary" variant="tonal">{{ item.current_user_role }}</v-chip>
      </template>
      <template #item.created_at="{ item }">
        {{ new Date(item.created_at).toLocaleDateString() }}
      </template>
      <template #item.actions="{ item }">
        <v-btn size="small" variant="text" color="primary" @click="openProject(item.id)">Open</v-btn>
      </template>
    </v-data-table>
  </UiParentCard>

  <ProjectFormDialog v-model="showCreateDialog" @created="handleProjectCreated" />
</template>
