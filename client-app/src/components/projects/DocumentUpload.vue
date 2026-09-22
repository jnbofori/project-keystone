<script setup lang="ts">
import { computed, ref } from 'vue';
import { SUPPORTED_EXTENSIONS } from '@/api/types';
import { documentsApi } from '@/api';
import { useSnackbar } from '@/composables/useSnackbar';
import { getErrorMessage } from '@/utils/apiError';
import type { Document } from '@/api/types';

const props = defineProps<{
  projectId: string;
}>();

const emit = defineEmits<{
  uploaded: [document: Document];
}>();

const { showSuccess, showError } = useSnackbar();
const file = ref<File | File[] | null>(null);
const uploading = ref(false);

const accept = SUPPORTED_EXTENSIONS.join(',');

const selectedFile = computed(() => {
  if (!file.value) return null;
  return Array.isArray(file.value) ? file.value[0] ?? null : file.value;
});

async function handleUpload() {
  const selected = selectedFile.value;
  if (!selected) {
    showError('Please select a file');
    return;
  }

  uploading.value = true;
  try {
    const document = await documentsApi.uploadDocument(props.projectId, selected);
    showSuccess(`${document.filename} uploaded`);
    file.value = null;
    emit('uploaded', document);
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to upload document'));
  } finally {
    uploading.value = false;
  }
}
</script>

<template>
  <v-card variant="outlined">
    <v-card-text>
      <div class="text-body-small text-medium-emphasis mb-3">
        Supported formats: {{ SUPPORTED_EXTENSIONS.join(', ') }}
      </div>
      <v-file-input
        v-model="file"
        label="Choose document"
        :accept="accept"
        prepend-icon=""
        prepend-inner-icon="$file"
        show-size
        hide-details="auto"
      />
      <v-btn
        color="primary"
        variant="flat"
        class="mt-4"
        :loading="uploading"
        :disabled="!selectedFile"
        @click="handleUpload"
      >
        Upload
      </v-btn>
    </v-card-text>
  </v-card>
</template>
