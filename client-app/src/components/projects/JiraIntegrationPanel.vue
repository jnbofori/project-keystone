<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { jiraApi } from '@/api';
import type { JiraConnection, JiraProjectSummary, JiraSyncResponse } from '@/api/types';
import { useSnackbar } from '@/composables/useSnackbar';
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

const loading = ref(false);
const connecting = ref(false);
const disconnecting = ref(false);
const selectingCloud = ref(false);
const loadingProjects = ref(false);
const linking = ref(false);
const syncing = ref(false);

const connection = ref<JiraConnection | null>(null);
const selectedCloudId = ref<string | null>(null);
const jiraProjects = ref<JiraProjectSummary[]>([]);
const selectedJiraKey = ref<string | null>(null);
const lastSync = ref<JiraSyncResponse | null>(null);

const connected = computed(() => Boolean(connection.value?.connected));
const needsSite = computed(() => Boolean(connection.value?.needs_site_selection));
const hasSite = computed(() => Boolean(connection.value?.cloud_id));
const siteOptions = computed(() => connection.value?.available_sites ?? []);

const jiraProjectItems = computed(() =>
  jiraProjects.value.map((project) => ({
    title: `${project.key} — ${project.name}`,
    value: project.key
  }))
);

async function loadConnection() {
  loading.value = true;
  try {
    connection.value = await jiraApi.getConnection(props.projectId);
    selectedCloudId.value = connection.value.cloud_id;
    if (connection.value.connected && connection.value.cloud_id) {
      await loadJiraProjects();
    }
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to load Jira connection'));
    connection.value = { connected: false, cloud_id: null, site_url: null, site_name: null, token_expires_at: null, connected_by: null, needs_site_selection: false, available_sites: [] };
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

async function connect() {
  connecting.value = true;
  try {
    const { authorize_url } = await jiraApi.startOAuth(props.projectId);
    window.location.href = authorize_url;
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to start Jira OAuth'));
    connecting.value = false;
  }
}

async function disconnect() {
  disconnecting.value = true;
  try {
    await jiraApi.disconnect(props.projectId);
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
    jiraProjects.value = [];
    selectedJiraKey.value = null;
    lastSync.value = null;
    emit('linked', null);
    showSuccess('Jira disconnected');
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to disconnect Jira'));
  } finally {
    disconnecting.value = false;
  }
}

async function saveCloud() {
  if (!selectedCloudId.value) {
    showError('Select an Atlassian site');
    return;
  }
  selectingCloud.value = true;
  try {
    connection.value = await jiraApi.selectCloud(props.projectId, selectedCloudId.value);
    showSuccess('Atlassian site selected');
    await loadJiraProjects();
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to select Atlassian site'));
  } finally {
    selectingCloud.value = false;
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
      <div v-if="!connected" class="d-flex flex-column ga-3">
        <p class="text-medium-emphasis mb-0">
          Connect this Keystone project to Atlassian with OAuth. An admin connects once; sync uses that connection.
        </p>
        <div>
          <v-btn color="primary" variant="flat" :loading="connecting" @click="connect">
            Connect to Jira
          </v-btn>
        </div>
      </div>

      <div v-else class="d-flex flex-column ga-6">
        <div class="d-flex flex-wrap align-center justify-space-between ga-3">
          <div>
            <div class="d-flex align-center ga-2 mb-1">
              <v-chip color="success" variant="tonal" size="small">Connected</v-chip>
              <span v-if="connection?.site_name" class="font-weight-medium">{{ connection.site_name }}</span>
            </div>
            <div v-if="connection?.site_url" class="text-body-2 text-medium-emphasis">
              {{ connection.site_url }}
            </div>
          </div>
          <v-btn color="error" variant="tonal" :loading="disconnecting" @click="disconnect">
            Disconnect
          </v-btn>
        </div>

        <v-card v-if="needsSite" variant="outlined">
          <v-card-title class="text-subtitle-1">Select Atlassian site</v-card-title>
          <v-card-text>
            <v-select
              v-model="selectedCloudId"
              :items="siteOptions"
              :item-title="(item: { site_name: string | null; site_url: string | null }) => item.site_name || item.site_url || 'Site'"
              item-value="cloud_id"
              label="Atlassian site"
              variant="outlined"
              density="comfortable"
              hide-details="auto"
            />
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn color="primary" variant="flat" :loading="selectingCloud" @click="saveCloud">
              Save site
            </v-btn>
          </v-card-actions>
        </v-card>

        <template v-if="hasSite">
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
        </template>
      </div>
    </template>
  </UiParentCard>
</template>
