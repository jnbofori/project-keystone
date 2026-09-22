<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import BaseBreadcrumb from '@/components/shared/BaseBreadcrumb.vue';
import UiParentCard from '@/components/shared/UiParentCard.vue';
import { useSnackbar } from '@/composables/useSnackbar';

const route = useRoute();
const router = useRouter();
const { showSuccess, showError } = useSnackbar();

const status = computed(() => String(route.query.status ?? ''));
const projectId = computed(() => {
  const value = route.query.project_id;
  return typeof value === 'string' && value ? value : null;
});
const needsSite = computed(() => String(route.query.needs_site ?? '') === '1');
const message = computed(() => {
  const value = route.query.message;
  return typeof value === 'string' ? value : null;
});

const handled = ref(false);
const isError = computed(() => status.value === 'error');
const isSuccess = computed(() => status.value === 'success');

const breadcrumbs = [
  { title: 'Home', disabled: false, href: '/dashboard/default' },
  { title: 'Jira Connection', disabled: true, href: '#' }
];

onMounted(() => {
  handled.value = true;

  if (isSuccess.value) {
    const suffix = needsSite.value ? ' Select an Atlassian site to finish setup.' : '';
    showSuccess(`Jira connected successfully.${suffix}`);
    if (projectId.value) {
      void router.replace({
        path: `/projects/${projectId.value}`,
        query: { tab: 'jira' }
      });
      return;
    }
    void router.replace('/projects');
    return;
  }

  if (isError.value) {
    showError(message.value || 'Jira OAuth failed');
  }
});
</script>

<template>
  <BaseBreadcrumb title="Jira Connection" :breadcrumbs="breadcrumbs" />

  <UiParentCard title="Jira OAuth">
    <v-progress-linear v-if="!handled" indeterminate color="primary" class="mb-4" />

    <v-alert v-if="isSuccess" type="success" variant="tonal" class="mb-4">
      Jira connected successfully.
      <span v-if="needsSite"> Select an Atlassian site on the project Jira tab to finish setup.</span>
      <span v-if="projectId"> Redirecting to the project…</span>
    </v-alert>

    <v-alert v-else-if="isError" type="error" variant="tonal" class="mb-4">
      {{ message || 'Jira OAuth failed. Please try connecting again from a project.' }}
    </v-alert>

    <v-alert v-else type="info" variant="tonal" class="mb-4">
      Waiting for OAuth result. If you arrived here manually, open a project and use the Jira tab to connect.
    </v-alert>

    <div class="d-flex ga-3">
      <v-btn
        v-if="projectId"
        color="primary"
        variant="flat"
        :to="`/projects/${projectId}?tab=jira`"
      >
        Open project Jira tab
      </v-btn>
      <v-btn variant="tonal" to="/projects">Back to projects</v-btn>
    </div>
  </UiParentCard>
</template>
