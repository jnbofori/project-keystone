<script setup lang="ts">
import { ref } from 'vue';
import { queriesApi } from '@/api';
import { useSnackbar } from '@/composables/useSnackbar';
import { getErrorMessage } from '@/utils/apiError';
import type { Query } from '@/api/types';

const props = defineProps<{
  projectId: string;
  disabled?: boolean;
  disabledMessage?: string;
}>();

const emit = defineEmits<{
  asked: [query: Query];
}>();

const { showError } = useSnackbar();
const question = ref('');
const asking = ref(false);

async function handleAsk() {
  const trimmed = question.value.trim();
  if (!trimmed) return;

  asking.value = true;
  try {
    const query = await queriesApi.askQuestion(props.projectId, { question: trimmed });
    question.value = '';
    emit('asked', query);
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to ask question'));
  } finally {
    asking.value = false;
  }
}
</script>

<template>
  <v-card variant="outlined" class="query-panel">
    <v-card-text>
      <v-alert v-if="disabled" type="warning" variant="tonal" class="mb-4">
        {{ disabledMessage || 'Upload and process documents before asking questions.' }}
      </v-alert>

      <v-textarea
        v-model="question"
        label="Ask a question about your project documents"
        rows="3"
        auto-grow
        hide-details="auto"
        :disabled="disabled || asking"
      />
      <div class="d-flex justify-end mt-3">
        <v-btn
          color="primary"
          variant="flat"
          :loading="asking"
          :disabled="disabled || !question.trim()"
          @click="handleAsk"
        >
          Ask
        </v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>
