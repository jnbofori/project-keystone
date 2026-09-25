<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { dashboardApi } from '@/api';
import type { ProjectDashboard, SprintInsights } from '@/api/types';
import { useSnackbar } from '@/composables/useSnackbar';
import { getErrorMessage } from '@/utils/apiError';
import UiParentCard from '@/components/shared/UiParentCard.vue';

const props = defineProps<{
  projectId: string;
}>();

const { showError } = useSnackbar();
const loading = ref(false);
const dashboard = ref<ProjectDashboard | null>(null);

const insightsLoading = ref(false);
const insightsError = ref<string | null>(null);
const insights = ref<SprintInsights | null>(null);

const paceColor = computed(() => {
  const label = dashboard.value?.risks.pace_label;
  if (label === 'Ahead') return 'success';
  if (label === 'Behind') return 'error';
  if (label === 'On track') return 'primary';
  return 'default';
});

const progressValue = computed(() => dashboard.value?.progress.percent ?? 0);
const timeValue = computed(() => dashboard.value?.time.elapsed_percent ?? 0);

const showInsightsCard = computed(() => Boolean(dashboard.value?.active_sprint));

function riskLevelColor(level: string | null | undefined): string {
  if (level === 'high') return 'error';
  if (level === 'medium') return 'warning';
  if (level === 'low') return 'success';
  return 'default';
}

function formatRiskLevel(level: string | null | undefined): string {
  if (!level) return 'Unavailable';
  return level.charAt(0).toUpperCase() + level.slice(1);
}

const scopeSignalCaption = computed(() => {
  const scope = dashboard.value?.risk_indicators?.scope;
  if (!scope) return '';
  const parts: string[] = [];
  if (scope.issues_added) parts.push(`+${scope.issues_added} added`);
  if (scope.issues_removed) parts.push(`−${scope.issues_removed} removed`);
  if (scope.semantic_expansions) parts.push(`${scope.semantic_expansions} req. expansions`);
  if (scope.new_dependencies) parts.push(`${scope.new_dependencies} new deps`);
  if (scope.points_increased_events) parts.push(`${scope.points_increased_events} points↑`);
  return parts.join(' · ');
});

const insightParagraphs = computed(() => {
  const text = insights.value?.insight?.trim();
  if (!text) return [];
  return text.split(/\n\s*\n/).map((part) => part.trim()).filter(Boolean);
});

async function loadInsights() {
  if (!props.projectId || !dashboard.value?.active_sprint) {
    insights.value = null;
    insightsError.value = null;
    return;
  }
  insightsLoading.value = true;
  insightsError.value = null;
  try {
    insights.value = await dashboardApi.getSprintInsights(props.projectId);
  } catch (error) {
    insights.value = null;
    insightsError.value = getErrorMessage(error, 'Failed to generate sprint insights');
  } finally {
    insightsLoading.value = false;
  }
}

async function load() {
  if (!props.projectId) return;
  loading.value = true;
  insights.value = null;
  insightsError.value = null;
  try {
    dashboard.value = await dashboardApi.getProjectDashboard(props.projectId);
    void loadInsights();
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

      <UiParentCard
        v-if="dashboard.risk_indicators"
        title="Risk indicators"
        class="mt-4"
      >
        <v-row>
          <v-col cols="12" md="4">
            <v-card variant="outlined" class="h-100">
              <v-card-text>
                <div class="d-flex align-center justify-space-between mb-2">
                  <div class="text-body-2 text-medium-emphasis">Delivery</div>
                  <v-chip
                    size="small"
                    variant="tonal"
                    :color="riskLevelColor(dashboard.risk_indicators.delivery.level)"
                  >
                    {{ formatRiskLevel(dashboard.risk_indicators.delivery.level) }}
                  </v-chip>
                </div>
                <div class="text-h5 mb-1">
                  {{
                    dashboard.risk_indicators.delivery.velocity_ratio !== null
                      ? `${dashboard.risk_indicators.delivery.velocity_ratio}x`
                      : '—'
                  }}
                </div>
                <div class="text-caption text-medium-emphasis">
                  Required {{ formatPoints(dashboard.risk_indicators.delivery.required_velocity) }}
                  vs hist. {{ formatPoints(dashboard.risk_indicators.delivery.historical_velocity) }}
                  · {{ formatPoints(dashboard.risk_indicators.delivery.remaining_points) }} pts left
                </div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="4">
            <v-card variant="outlined" class="h-100">
              <v-card-text>
                <div class="d-flex align-center justify-space-between mb-2 flex-wrap ga-2">
                  <div class="text-body-2 text-medium-emphasis">Scope</div>
                  <div class="d-flex flex-wrap ga-1">
                    <v-chip
                      v-if="dashboard.risk_indicators.scope.creep_detected"
                      size="small"
                      variant="tonal"
                      color="warning"
                    >
                      Scope creep detected
                    </v-chip>
                    <v-chip
                      size="small"
                      variant="tonal"
                      :color="riskLevelColor(dashboard.risk_indicators.scope.level)"
                    >
                      {{ formatRiskLevel(dashboard.risk_indicators.scope.level) }}
                    </v-chip>
                  </div>
                </div>
                <div class="text-h5 mb-1">
                  {{
                    dashboard.risk_indicators.scope.scope_growth_percent !== null
                      ? `+${dashboard.risk_indicators.scope.scope_growth_percent}%`
                      : '—'
                  }}
                </div>
                <div class="text-caption text-medium-emphasis mb-1">
                  {{ formatPoints(dashboard.risk_indicators.scope.baseline_points) }}
                  → {{ formatPoints(dashboard.risk_indicators.scope.current_points) }} pts
                  (+{{ formatPoints(dashboard.risk_indicators.scope.scope_added_points) }} mid-sprint)
                </div>
                <div
                  v-if="dashboard.risk_indicators.scope.summary"
                  class="text-body-2 mb-1"
                >
                  {{ dashboard.risk_indicators.scope.summary }}
                </div>
                <div v-if="scopeSignalCaption" class="text-caption text-medium-emphasis">
                  {{ scopeSignalCaption }}
                </div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" md="4">
            <v-card variant="outlined" class="h-100">
              <v-card-text>
                <div class="d-flex align-center justify-space-between mb-2">
                  <div class="text-body-2 text-medium-emphasis">Dependency</div>
                  <v-chip
                    size="small"
                    variant="tonal"
                    :color="riskLevelColor(dashboard.risk_indicators.dependency.level)"
                  >
                    {{ formatRiskLevel(dashboard.risk_indicators.dependency.level) }}
                  </v-chip>
                </div>
                <div class="text-h5 mb-1">
                  {{
                    dashboard.risk_indicators.dependency.unavailable_reason
                      ? '—'
                      : dashboard.risk_indicators.dependency.at_risk_count
                  }}
                </div>
                <div class="text-caption text-medium-emphasis">
                  <template v-if="dashboard.risk_indicators.dependency.unavailable_reason">
                    {{ dashboard.risk_indicators.dependency.unavailable_reason }}
                  </template>
                  <template v-else>
                    {{ dashboard.risk_indicators.dependency.at_risk_count }} at risk ·
                    {{ dashboard.risk_indicators.dependency.open_dependency_count }} open deps
                  </template>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </UiParentCard>

      <UiParentCard v-if="showInsightsCard" title="Sprint intelligence" class="mt-4">
        <v-progress-linear v-if="insightsLoading" indeterminate color="primary" class="mb-4" />

        <v-alert v-else-if="insightsError" type="warning" variant="tonal" class="mb-0">
          <div class="d-flex flex-wrap align-center justify-space-between ga-3">
            <span>{{ insightsError }}</span>
            <v-btn size="small" variant="tonal" :loading="insightsLoading" @click="loadInsights">
              Retry
            </v-btn>
          </div>
        </v-alert>

        <template v-else-if="insightParagraphs.length">
          <p
            v-for="(paragraph, index) in insightParagraphs"
            :key="index"
            class="text-body-1 mb-3"
            :class="{ 'mb-0': index === insightParagraphs.length - 1 }"
          >
            {{ paragraph }}
          </p>
        </template>

        <div v-else class="text-medium-emphasis">No insight available yet.</div>
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

      <v-row class="mt-2">
        <v-col cols="12" md="6">
          <UiParentCard title="Due-date risk">
            <div v-if="!dashboard.flow.due_soon.length" class="text-medium-emphasis">
              No upcoming or overdue due dates.
            </div>
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
