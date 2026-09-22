<script setup lang="ts">
import { computed } from 'vue';
import type { Document } from '@/api/types';

const props = defineProps<{
  documents: Document[];
  loading?: boolean;
  canDelete?: boolean;
}>();

const emit = defineEmits<{
  delete: [documentId: string];
}>();

const headers = [
  { title: 'Filename', key: 'filename' },
  { title: 'Status', key: 'status' },
  { title: 'Chunks', key: 'chunk_count', align: 'end' as const },
  { title: 'Uploaded', key: 'created_at' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' as const }
];

const statusColor = computed(() => ({
  pending: 'warning',
  processing: 'info',
  ready: 'success',
  failed: 'error'
}));
</script>

<template>
  <v-data-table
    :headers="headers"
    :items="documents"
    :loading="loading"
    item-value="id"
    class="elevation-0"
    mobile-breakpoint="md"
  >
    <template #item.status="{ item }">
      <v-chip size="small" :color="statusColor[item.status]" variant="tonal">
        {{ item.status }}
      </v-chip>
    </template>

    <template #item.created_at="{ item }">
      {{ new Date(item.created_at).toLocaleString() }}
    </template>

    <template #item.filename="{ item }">
      <div>
        <div>{{ item.filename }}</div>
        <div v-if="item.error_message" class="text-caption text-error">{{ item.error_message }}</div>
      </div>
    </template>

    <template #item.actions="{ item }">
      <v-btn
        v-if="canDelete"
        size="small"
        color="error"
        variant="text"
        @click="emit('delete', item.id)"
      >
        Delete
      </v-btn>
    </template>

    <template #no-data>
      <v-alert type="info" variant="tonal" class="ma-4">No documents uploaded yet.</v-alert>
    </template>
  </v-data-table>
</template>
