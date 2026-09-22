<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { LogoutIcon } from 'vue-tabler-icons';
import { useAuthStore } from '@/stores/auth';

const router = useRouter();
const auth = useAuthStore();

const greeting = computed(() => {
  const email = auth.user?.email ?? 'User';
  return email.split('@')[0];
});

function logout() {
  auth.logout();
  router.push('/authentication/login');
}
</script>

<template>
  <div class="pt-4">
    <div class="px-4">
      <h4 class="mb-n1">
        Welcome, <span class="font-weight-regular">{{ greeting }}</span>
      </h4>
      <span class="text-body-small text-medium-emphasis">{{ auth.user?.email }}</span>
    </div>

    <v-divider class="mx-4 my-3" />

    <v-list class="px-2">
      <v-list-item color="secondary" rounded="md" @click="logout">
        <template #prepend>
          <LogoutIcon size="20" class="mr-2" />
        </template>
        <v-list-item-title class="text-body-small">Logout</v-list-item-title>
      </v-list-item>
    </v-list>
  </div>
</template>
