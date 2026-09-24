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
  { title: 'Organization', disabled: false, href: '/settings/organization' },
  { title: 'Jira OAuth', disabled: true, href: '#' }
];

onMounted(() => {
  handled.value = true;

  if (isSuccess.value) {
    const suffix = needsSite.value ? ' Select an Atlassian site to finish setup.' : '';
    showSuccess(`Jira connected successfully.${suffix}`);
    void router.replace({
      path: '/settings/organization',
      query: { section: 'jira' }
    });
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
      <span v-if="needsSite"> Select an Atlassian site in Organization settings to finish setup.</span>
      Redirecting…
    </v-alert>

    <v-alert v-else-if="isError" type="error" variant="tonal" class="mb-4">
      {{ message || 'Jira OAuth failed. Please try connecting again from Organization settings.' }}
    </v-alert>

    <v-alert v-else type="info" variant="tonal" class="mb-4">
      Waiting for OAuth result. If you arrived here manually, open Organization settings to connect
      Jira.
    </v-alert>

    <div class="d-flex ga-3">
      <v-btn
        color="primary"
        variant="flat"
        :to="{ path: '/settings/organization', query: { section: 'jira' } }"
      >
        Open organization settings
      </v-btn>
      <v-btn variant="tonal" to="/projects">Back to projects</v-btn>
    </div>
  </UiParentCard>
</template>
