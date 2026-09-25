<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { dashboardApi } from '@/api';
import type { ProjectDashboard } from '@/api/types';
import { useSnackbar } from '@/composables/useSnackbar';
import { getErrorMessage } from '@/utils/apiError';
import UiParentCard from '@/components/shared/UiParentCard.vue';

const props = defineProps<{
  projectId: string;
}>();

const { showError } = useSnackbar();
const loading = ref(false);
const dashboard = ref<ProjectDashboard | null>(null);

const paceColor = computed(() => {
  const label = dashboard.value?.risks.pace_label;
  if (label === 'Ahead') return 'success';
  if (label === 'Behind') return 'error';
  if (label === 'On track') return 'primary';
  return 'default';
});

const progressValue = computed(() => dashboard.value?.progress.percent ?? 0);
const timeValue = computed(() => dashboard.value?.time.elapsed_percent ?? 0);

async function load() {
  if (!props.projectId) return;
  loading.value = true;
  try {
    dashboard.value = await dashboardApi.getProjectDashboard(props.projectId);
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to load delivery dashboard'));
    dashboard.value = null;
  } finally {
    loading.value = false;
  }
}

function formatPoints(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

onMounted(load);
watch(
  () => props.projectId,
  () => {
    void load();
  }
);

defineExpose({ reload: load });
</script>

<template>
  <div>
    <v-progress-linear v-if="loading && !dashboard" indeterminate color="primary" class="mb-4" />

    <v-alert v-if="dashboard?.message" type="info" variant="tonal" class="mb-4">
      {{ dashboard.message }}
    </v-alert>

    <template v-if="dashboard">
      <UiParentCard
        :title="dashboard.active_sprint ? `Sprint: ${dashboard.active_sprint.name}` : 'Delivery'"
      >
        <div class="d-flex flex-wrap align-center ga-3 mb-4">
          <v-chip
            v-if="dashboard.risks.pace_label"
            :color="paceColor"
            variant="tonal"
            size="small"
          >
            {{ dashboard.risks.pace_label }}
            <span v-if="dashboard.risks.pace_gap !== null" class="ms-1">
              ({{ dashboard.risks.pace_gap > 0 ? '+' : '' }}{{ dashboard.risks.pace_gap }}%)
            </span>
          </v-chip>
          <v-chip
            v-if="dashboard.risks.carryover_likely"
            color="warning"
            variant="tonal"
            size="small"
          >
            Carryover likely
          </v-chip>
          <span v-if="dashboard.time.days_remaining !== null" class="text-medium-emphasis">
            {{ dashboard.time.days_remaining }} days remaining
          </span>
        </div>

        <v-row>
          <v-col cols="12" md="6">
            <div class="text-body-2 text-medium-emphasis mb-1">Progress</div>
            <div class="text-h5 mb-2">
              {{ dashboard.progress.percent !== null ? `${dashboard.progress.percent}%` : '—' }}
            </div>
            <v-progress-linear
              :model-value="progressValue"
              color="primary"
              height="10"
              rounded
              class="mb-2"
            />
            <div class="text-body-2">
              Completed points:
              <strong>
                {{ formatPoints(dashboard.progress.completed_points) }}
                /
                {{ formatPoints(dashboard.progress.total_points) }}
              </strong>
              <span v-if="!dashboard.progress.uses_points" class="text-medium-emphasis">
                ({{ dashboard.progress.completed_count }}/{{ dashboard.progress.total_count }} items)
              </span>
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <div class="text-body-2 text-medium-emphasis mb-1">Time elapsed</div>
            <div class="text-h5 mb-2">
              {{
                dashboard.time.elapsed_percent !== null
                  ? `${dashboard.time.elapsed_percent}%`
                  : '—'
              }}
            </div>
            <v-progress-linear
              :model-value="timeValue"
              color="secondary"
              height="10"
              rounded
            />
          </v-col>
        </v-row>
      </UiParentCard>

      <v-row class="mt-2">
        <v-col cols="12" md="4">
          <v-card variant="outlined" class="h-100">
            <v-card-text>
              <div class="text-body-2 text-medium-emphasis">Velocity — last sprint</div>
              <div class="text-h4">{{ formatPoints(dashboard.velocity.last_sprint_points) }}</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card variant="outlined" class="h-100">
            <v-card-text>
              <div class="text-body-2 text-medium-emphasis">3-sprint avg</div>
              <div class="text-h4">{{ formatPoints(dashboard.velocity.avg_3_sprint) }}</div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card variant="outlined" class="h-100">
            <v-card-text>
              <div class="text-body-2 text-medium-emphasis">Current forecast</div>
              <div class="text-h4">{{ formatPoints(dashboard.velocity.forecast_current) }}</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <UiParentCard title="Attention" class="mt-4">
        <v-row>
          <v-col cols="6" sm="3">
            <div class="text-body-2 text-medium-emphasis">Blocked tasks</div>
            <div class="text-h5">{{ dashboard.risks.blocked_count }}</div>
            <div v-if="dashboard.risks.stale_blocked_count" class="text-caption text-warning">
              {{ dashboard.risks.stale_blocked_count }} stale
            </div>
          </v-col>
          <v-col cols="6" sm="3">
            <div class="text-body-2 text-medium-emphasis">Scope added (est.)</div>
            <div class="text-h5">+{{ formatPoints(dashboard.risks.scope_added_points) }}</div>
          </v-col>
          <v-col cols="6" sm="3">
            <div class="text-body-2 text-medium-emphasis">Reopened</div>
            <div class="text-h5">{{ dashboard.risks.reopened_count }}</div>
            <div v-if="dashboard.risks.reopen_rate !== null" class="text-caption text-medium-emphasis">
              rate {{ dashboard.risks.reopen_rate }}
            </div>
          </v-col>
          <v-col cols="6" sm="3">
            <div class="text-body-2 text-medium-emphasis">Pace gap</div>
            <div class="text-h5">
              {{
                dashboard.risks.pace_gap !== null
                  ? `${dashboard.risks.pace_gap > 0 ? '+' : ''}${dashboard.risks.pace_gap}%`
                  : '—'
              }}
            </div>
          </v-col>
        </v-row>
      </UiParentCard>

      <v-row class="mt-2">
        <v-col cols="12" md="4">
          <UiParentCard title="Flow by status">
            <div v-if="!dashboard.flow.by_status.length" class="text-medium-emphasis">No tasks in sprint.</div>
            <div v-for="row in dashboard.flow.by_status" :key="row.status" class="d-flex justify-space-between mb-2">
              <span class="text-capitalize">{{ row.status.replaceAll('_', ' ') }}</span>
              <strong>{{ row.count }}</strong>
            </div>
          </UiParentCard>
        </v-col>
        <v-col cols="12" md="4">
          <UiParentCard title="Aging WIP">
            <div v-if="!dashboard.flow.aging_wip.length" class="text-medium-emphasis">
              No stuck in-progress items.
            </div>
            <div v-for="item in dashboard.flow.aging_wip" :key="item.id" class="mb-3">
              <div class="font-weight-medium text-truncate">{{ item.title }}</div>
              <div class="text-caption text-medium-emphasis">
                {{ item.status.replaceAll('_', ' ') }} · {{ item.days }} days
              </div>
            </div>
          </UiParentCard>
        </v-col>
        <v-col cols="12" md="4">
          <UiParentCard title="Assignee load">
            <div v-if="!dashboard.load.by_assignee.length" class="text-medium-emphasis">
              No open assignments.
            </div>
            <div
              v-for="row in dashboard.load.by_assignee"
              :key="row.assignee_id || row.name"
              class="d-flex justify-space-between mb-2"
            >
              <span class="text-truncate me-2">{{ row.name }}</span>
              <span class="text-no-wrap">
                {{ formatPoints(row.open_points) }} pts · {{ row.open_tasks }}
              </span>
            </div>
          </UiParentCard>
        </v-col>
      </v-row>

      <v-row v-if="dashboard.flow.due_soon.length || dashboard.epic_health.length" class="mt-2">
        <v-col v-if="dashboard.flow.due_soon.length" cols="12" md="6">
          <UiParentCard title="Due-date risk">
            <div v-for="item in dashboard.flow.due_soon" :key="item.id" class="mb-3">
              <div class="font-weight-medium text-truncate">{{ item.title }}</div>
              <div class="text-caption text-medium-emphasis">
                Due {{ new Date(item.due_date).toLocaleDateString() }} ·
                {{ item.status.replaceAll('_', ' ') }}
              </div>
            </div>
          </UiParentCard>
        </v-col>
        <v-col v-if="dashboard.epic_health.length" cols="12" md="6">
          <UiParentCard title="Epic health">
            <div v-for="epic in dashboard.epic_health" :key="epic.id" class="mb-3">
              <div class="d-flex justify-space-between mb-1">
                <span class="text-truncate me-2">{{ epic.title }}</span>
                <span class="text-no-wrap">
                  {{ epic.done_stories }}/{{ epic.total_stories }}
                </span>
              </div>
              <v-progress-linear
                :model-value="epic.percent_done ?? 0"
                color="primary"
                height="6"
                rounded
              />
            </div>
          </UiParentCard>
        </v-col>
      </v-row>
    </template>
  </div>
</template>
