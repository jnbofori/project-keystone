<script setup lang="ts">
import { computed, ref } from 'vue';
import type { Query } from '@/api/types';
import { uniqueSourceFilenames } from '@/utils/sources';
import FormattedAnswer from '@/components/projects/FormattedAnswer.vue';

const props = defineProps<{
  queries: Query[];
  loading?: boolean;
}>();

const expanded = ref<string[]>([]);

const sortedQueries = computed(() =>
  [...props.queries].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
);

const displayQueries = computed(() =>
  sortedQueries.value.map((query) => ({
    query,
    sourceFilenames: uniqueSourceFilenames(query.sources)
  }))
);
</script>

<template>
  <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

  <v-alert v-if="!loading && sortedQueries.length === 0" type="info" variant="tonal">
    No questions asked yet. Submit a question below to start the conversation.
  </v-alert>

  <v-expansion-panels v-else v-model="expanded" multiple class="mb-4">
    <v-expansion-panel v-for="{ query, sourceFilenames } in displayQueries" :key="query.id" :value="query.id">
      <v-expansion-panel-title>
        <div class="text-truncate">{{ query.question }}</div>
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <div class="text-body-small text-medium-emphasis mb-2">
          {{ new Date(query.created_at).toLocaleString() }}
        </div>
        <FormattedAnswer :text="query.answer" class="mb-4" />
        <div v-if="sourceFilenames.length" class="text-subtitle-2 mb-2">Sources</div>
        <div v-if="sourceFilenames.length" class="d-flex flex-wrap ga-2">
          <v-chip v-for="filename in sourceFilenames" :key="filename" size="small" color="primary" variant="tonal">
            {{ filename }}
          </v-chip>
        </div>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>
