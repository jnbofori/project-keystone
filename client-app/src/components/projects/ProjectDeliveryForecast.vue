<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { dashboardApi } from '@/api';
import type { ProjectDeliveryForecast } from '@/api/types';
import { useSnackbar } from '@/composables/useSnackbar';
import { getErrorMessage } from '@/utils/apiError';
import UiParentCard from '@/components/shared/UiParentCard.vue';

const props = defineProps<{
  projectId: string;
}>();

const { showError } = useSnackbar();
const loading = ref(false);
const forecast = ref<ProjectDeliveryForecast | null>(null);

const isAverageMethod = computed(
  () => forecast.value?.method === 'average_velocity'
);

function formatDate(value: string | null | undefined): string {
  if (!value) return '—';
  const d = new Date(`${value}T00:00:00`);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function formatRemaining(value: number, unit: string): string {
  const rounded = Number.isInteger(value) ? String(value) : value.toFixed(1);
  return unit === 'items' ? `${rounded} items` : `${rounded} pts`;
}

function formatVelocity(value: number | null | undefined, unit: string): string {
  if (value === null || value === undefined) return '—';
  const rounded = Number.isInteger(value) ? String(value) : value.toFixed(1);
  return unit === 'items' ? `${rounded} items/sprint` : `${rounded} pts/sprint`;
}

const caption = computed(() => {
  if (!forecast.value) return '';
  const f = forecast.value;
  if (f.method === 'average_velocity') {
    const parts = [
      formatRemaining(f.remaining, f.unit),
      `avg ${formatVelocity(f.average_velocity, f.unit)}`,
    ];
    if (f.likely_sprints != null) {
      parts.push(`~${f.likely_sprints} sprints`);
    }
    parts.push('Average velocity');
    return parts.join(' · ');
  }
  const parts = [
    formatRemaining(f.remaining, f.unit),
    `${f.samples_used} historical samples`,
    'Monte Carlo',
  ];
  return parts.join(' · ');
});

async function load() {
  if (!props.projectId) return;
  loading.value = true;
  try {
    forecast.value = await dashboardApi.getDeliveryForecast(props.projectId);
  } catch (error) {
    forecast.value = null;
    showError(getErrorMessage(error, 'Failed to load delivery forecast'));
  } finally {
    loading.value = false;
  }
}

onMounted(load);
watch(
  () => props.projectId,
  () => {
    void load();
  }
);
</script>

<template>
  <div>
    <v-progress-linear v-if="loading && !forecast" indeterminate color="primary" class="mb-4" />

    <UiParentCard title="Project delivery forecast">
      <template v-if="forecast">
        <v-alert
          v-if="forecast.already_complete"
          type="success"
          variant="tonal"
          class="mb-0"
        >
          No open backlog remaining — project delivery work looks complete.
        </v-alert>

        <v-alert
          v-else-if="forecast.unavailable_reason"
          type="info"
          variant="tonal"
          class="mb-0"
        >
          {{ forecast.unavailable_reason }}
          <div class="text-caption mt-2">
            Remaining backlog: {{ formatRemaining(forecast.remaining, forecast.unit) }}.
            Sync completed sprints from Jira to unlock the forecast.
          </div>
        </v-alert>

        <template v-else>
          <div class="text-body-2 text-medium-emphasis mb-1">Likely delivery</div>
          <div class="text-h3 mb-4">{{ formatDate(forecast.p50_date) }}</div>

          <template v-if="isAverageMethod">
            <v-alert type="info" variant="tonal" density="comfortable" class="mb-3">
              Estimate uses average sprint velocity
              <template v-if="forecast.estimated_sprints != null">
                ({{ forecast.estimated_sprints }} → ~{{ forecast.likely_sprints }} sprints).
              </template>
              p85 / p95 need 3+ completed sprints for Monte Carlo.
            </v-alert>
          </template>
          <v-row v-else class="mb-2">
            <v-col cols="12" sm="6">
              <div class="text-body-2 text-medium-emphasis">p85</div>
              <div class="text-h5">{{ formatDate(forecast.p85_date) }}</div>
            </v-col>
            <v-col cols="12" sm="6">
              <div class="text-body-2 text-medium-emphasis">p95</div>
              <div class="text-h5">{{ formatDate(forecast.p95_date) }}</div>
            </v-col>
          </v-row>

          <div class="text-caption text-medium-emphasis">
            {{ caption }}
            <span v-if="forecast.trials"> · {{ forecast.trials.toLocaleString() }} trials</span>
          </div>
        </template>
      </template>

      <div v-else-if="!loading" class="text-medium-emphasis">
        Delivery forecast is unavailable.
      </div>
    </UiParentCard>
  </div>
</template>
