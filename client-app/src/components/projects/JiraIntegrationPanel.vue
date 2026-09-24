<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { jiraApi } from '@/api';
import type { JiraConnection, JiraProjectSummary, JiraSyncResponse } from '@/api/types';
import { useOrgRole } from '@/composables/useOrgRole';
import { useSnackbar } from '@/composables/useSnackbar';
import { useOrganizationStore } from '@/stores/organization';
import { getErrorMessage } from '@/utils/apiError';
import UiParentCard from '@/components/shared/UiParentCard.vue';

const props = defineProps<{
  projectId: string;
  linkedJiraKey?: string | null;
}>();

const emit = defineEmits<{
  linked: [jiraProjectKey: string | null];
}>();

const { showSuccess, showError } = useSnackbar();
const orgStore = useOrganizationStore();

const loading = ref(false);
const loadingProjects = ref(false);
const linking = ref(false);
const syncing = ref(false);

const connection = ref<JiraConnection | null>(null);
const jiraProjects = ref<JiraProjectSummary[]>([]);
const selectedJiraKey = ref<string | null>(null);
const lastSync = ref<JiraSyncResponse | null>(null);

const orgPermissions = computed(() => useOrgRole(orgStore.currentRole));
const connected = computed(() => Boolean(connection.value?.connected));
const needsSite = computed(() => Boolean(connection.value?.needs_site_selection));
const hasSite = computed(() => Boolean(connection.value?.cloud_id));

const jiraProjectItems = computed(() =>
  jiraProjects.value.map((project) => ({
    title: `${project.key} — ${project.name}`,
    value: project.key
  }))
);

async function ensureOrg() {
  if (!orgStore.organization) {
    try {
      await orgStore.fetchMe();
    } catch {
      // permissions messaging handles missing org role
    }
  }
}

async function loadConnection() {
  loading.value = true;
  try {
    await ensureOrg();
    try {
      connection.value = await jiraApi.getConnection();
    } catch (error) {
      // Project admins who are not org admins cannot read org connection; probe via list.
      try {
        jiraProjects.value = await jiraApi.listJiraProjects(props.projectId);
        connection.value = {
          connected: true,
          cloud_id: 'org',
          site_url: null,
          site_name: 'Organization Jira',
          token_expires_at: null,
          connected_by: null,
          needs_site_selection: false,
          available_sites: []
        };
        if (props.linkedJiraKey) {
          selectedJiraKey.value = props.linkedJiraKey;
        }
        return;
      } catch {
        const detail = getErrorMessage(error, '');
        if (!/insufficient|forbidden|403/i.test(detail)) {
          showError(detail || 'Failed to load Jira connection');
        }
        connection.value = {
          connected: false,
          cloud_id: null,
          site_url: null,
          site_name: null,
          token_expires_at: null,
          connected_by: null,
          needs_site_selection: false,
          available_sites: []
        };
        return;
      }
    }
    if (connection.value.connected && connection.value.cloud_id) {
      await loadJiraProjects();
    }
  } finally {
    loading.value = false;
  }
}

async function loadJiraProjects() {
  loadingProjects.value = true;
  try {
    jiraProjects.value = await jiraApi.listJiraProjects(props.projectId);
    if (props.linkedJiraKey) {
      selectedJiraKey.value = props.linkedJiraKey;
    }
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to list Jira projects'));
    jiraProjects.value = [];
  } finally {
    loadingProjects.value = false;
  }
}

async function saveLink() {
  linking.value = true;
  try {
    const result = await jiraApi.linkProject(props.projectId, selectedJiraKey.value);
    emit('linked', result.jira_project_key);
    showSuccess(
      result.jira_project_key
        ? `Linked to Jira project ${result.jira_project_key}`
        : 'Jira project unlinked'
    );
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to link Jira project'));
  } finally {
    linking.value = false;
  }
}

async function unlink() {
  selectedJiraKey.value = null;
  await saveLink();
}

async function sync() {
  syncing.value = true;
  lastSync.value = null;
  try {
    lastSync.value = await jiraApi.syncProject(props.projectId);
    const result = lastSync.value;
    showSuccess(
      `Synced ${result.tasks} tasks, ${result.stories} stories, ${result.epics} epics, ${result.sprints} sprints`
    );
  } catch (error) {
    showError(getErrorMessage(error, 'Jira sync failed'));
  } finally {
    syncing.value = false;
  }
}

watch(
  () => props.linkedJiraKey,
  (key) => {
    selectedJiraKey.value = key ?? null;
  }
);

onMounted(() => {
  selectedJiraKey.value = props.linkedJiraKey ?? null;
  void loadConnection();
});
</script>

<template>
  <UiParentCard title="Jira Integration">
    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <template v-else>
      <div v-if="!connected || needsSite || !hasSite" class="d-flex flex-column ga-3">
        <v-alert type="info" variant="tonal">
          <template v-if="orgPermissions.canConnectJira">
            Connect Jira for your organization first, then return here to link a project key.
          </template>
          <template v-else>
            Ask an organization admin to connect Jira under Organization settings. Once connected,
            you can link a Jira project key here.
          </template>
        </v-alert>
        <div>
          <v-btn
            color="primary"
            variant="flat"
            :to="{ path: '/settings/organization', query: { section: 'jira' } }"
          >
            Open organization settings
          </v-btn>
        </div>
      </div>

      <div v-else class="d-flex flex-column ga-6">
        <div>
          <div class="d-flex align-center ga-2 mb-1">
            <v-chip color="success" variant="tonal" size="small">Org connected</v-chip>
            <span v-if="connection?.site_name" class="font-weight-medium">{{ connection.site_name }}</span>
          </div>
          <div v-if="connection?.site_url" class="text-body-2 text-medium-emphasis">
            {{ connection.site_url }}
          </div>
        </div>

        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">Link Jira project</v-card-title>
          <v-card-text>
            <v-autocomplete
              v-model="selectedJiraKey"
              :items="jiraProjectItems"
              :loading="loadingProjects"
              label="Jira project"
              variant="outlined"
              density="comfortable"
              clearable
              hide-details="auto"
              no-data-text="No Jira projects available"
            />
            <div v-if="linkedJiraKey" class="text-body-2 text-medium-emphasis mt-3">
              Currently linked: <strong>{{ linkedJiraKey }}</strong>
            </div>
          </v-card-text>
          <v-card-actions>
            <v-btn variant="text" :disabled="!linkedJiraKey" :loading="linking" @click="unlink">
              Unlink
            </v-btn>
            <v-spacer />
            <v-btn
              color="primary"
              variant="flat"
              :loading="linking"
              :disabled="!selectedJiraKey"
              @click="saveLink"
            >
              Save link
            </v-btn>
          </v-card-actions>
        </v-card>

        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">Sync from Jira</v-card-title>
          <v-card-text>
            <p class="text-medium-emphasis mb-4">
              Pull team members, sprints, epics, stories, tasks, and project events into Keystone.
            </p>
            <v-btn
              color="primary"
              variant="flat"
              :loading="syncing"
              :disabled="!linkedJiraKey"
              @click="sync"
            >
              Sync now
            </v-btn>
            <v-alert v-if="!linkedJiraKey" type="info" variant="tonal" class="mt-4" density="comfortable">
              Link a Jira project before syncing.
            </v-alert>

            <div v-if="lastSync" class="mt-4">
              <div class="text-subtitle-2 mb-2">Last sync</div>
              <div class="d-flex flex-wrap ga-2">
                <v-chip size="small" variant="tonal">Members {{ lastSync.team_members }}</v-chip>
                <v-chip size="small" variant="tonal">Sprints {{ lastSync.sprints }}</v-chip>
                <v-chip size="small" variant="tonal">Epics {{ lastSync.epics }}</v-chip>
                <v-chip size="small" variant="tonal">Stories {{ lastSync.stories }}</v-chip>
                <v-chip size="small" variant="tonal">Tasks {{ lastSync.tasks }}</v-chip>
                <v-chip size="small" variant="tonal">Events {{ lastSync.events }}</v-chip>
              </div>
              <v-alert
                v-if="lastSync.errors.length"
                type="warning"
                variant="tonal"
                class="mt-3"
                density="comfortable"
              >
                {{ lastSync.errors.length }} partial error(s). First:
                {{ lastSync.errors[0].entity }}
                <span v-if="lastSync.errors[0].key"> ({{ lastSync.errors[0].key }})</span>
                — {{ lastSync.errors[0].message }}
              </v-alert>
            </div>
          </v-card-text>
        </v-card>
      </div>
    </template>
  </UiParentCard>
</template>
