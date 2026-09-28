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
const account = computed(() => {
  const value = route.query.account;
  return typeof value === 'string' ? value : null;
});
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
  { title: 'GitHub', disabled: true, href: '#' }
];

onMounted(() => {
  handled.value = true;

  if (isSuccess.value) {
    showSuccess(account.value ? `GitHub account ${account.value} connected.` : 'GitHub App installation updated.');
    void router.replace({
      path: '/settings/organization',
      query: { section: 'github' }
    });
    return;
  }

  if (isError.value) {
    showError(message.value || 'GitHub App installation failed');
  }
});
</script>

<template>
  <BaseBreadcrumb title="GitHub Connection" :breadcrumbs="breadcrumbs" />

  <UiParentCard title="GitHub App installation">
    <v-progress-linear v-if="!handled" indeterminate color="primary" class="mb-4" />

    <v-alert v-if="isSuccess" type="success" variant="tonal" class="mb-4">
      GitHub connected successfully. Redirecting…
    </v-alert>

    <v-alert v-else-if="isError" type="error" variant="tonal" class="mb-4">
      {{ message || 'GitHub App installation failed. Please try again from Organization settings.' }}
    </v-alert>

    <v-alert v-else type="info" variant="tonal" class="mb-4">
      Waiting for the installation result. If you arrived here manually, open Organization settings to
      connect GitHub.
    </v-alert>

    <div class="d-flex ga-3">
      <v-btn
        color="primary"
        variant="flat"
        :to="{ path: '/settings/organization', query: { section: 'github' } }"
      >
        Open organization settings
      </v-btn>
      <v-btn variant="tonal" to="/projects">Back to projects</v-btn>
    </div>
  </UiParentCard>
</template>
