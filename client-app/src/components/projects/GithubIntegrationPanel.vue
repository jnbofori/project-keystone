<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { githubApi } from '@/api';
import type {
  GithubActivityResponse,
  GithubInstallation,
  GithubLinkedRepo,
  GithubPullRequestStatus,
  GithubRepoSummary,
  GithubSyncResponse
} from '@/api/types';
import { useOrgRole } from '@/composables/useOrgRole';
import { useSnackbar } from '@/composables/useSnackbar';
import { useOrganizationStore } from '@/stores/organization';
import { getErrorMessage } from '@/utils/apiError';
import UiParentCard from '@/components/shared/UiParentCard.vue';

const props = defineProps<{
  projectId: string;
}>();

const { showSuccess, showError } = useSnackbar();
const orgStore = useOrganizationStore();

const loading = ref(false);
const loadingRepos = ref(false);
const saving = ref(false);
const syncing = ref(false);
const loadingActivity = ref(false);

const installations = ref<GithubInstallation[]>([]);
const availableRepos = ref<GithubRepoSummary[]>([]);
const linkedRepos = ref<GithubLinkedRepo[]>([]);
const selectedRepoIds = ref<number[]>([]);
const lastSync = ref<GithubSyncResponse | null>(null);
const activity = ref<GithubActivityResponse | null>(null);

const orgPermissions = computed(() => useOrgRole(orgStore.currentRole));
const hasInstallations = computed(() => installations.value.length > 0);

const repoItems = computed(() => {
  const items = availableRepos.value.map((repo) => ({
    title: repo.full_name,
    value: repo.repo_id,
    subtitle: `${repo.account_login}${repo.private ? ' · private' : ''}`
  }));
  for (const linked of linkedRepos.value) {
    if (!items.some((item) => item.value === linked.repo_id)) {
      items.push({ title: linked.full_name, value: linked.repo_id, subtitle: 'No longer accessible' });
    }
  }
  return items.sort((a, b) => a.title.localeCompare(b.title));
});

const selectionChanged = computed(() => {
  const current = new Set(linkedRepos.value.map((repo) => repo.repo_id));
  const next = new Set(selectedRepoIds.value);
  if (current.size !== next.size) return true;
  return [...next].some((id) => !current.has(id));
});

function prStatusColor(status: GithubPullRequestStatus, draft: boolean): string {
  if (draft && status === 'open') return 'default';
  if (status === 'merged') return 'secondary';
  if (status === 'closed') return 'error';
  return 'success';
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : 'Never';
}

async function ensureOrg() {
  if (!orgStore.organization) {
    try {
      await orgStore.fetchMe();
    } catch {
      // permissions messaging handles missing org role
    }
  }
}

async function loadAvailableRepos() {
  loadingRepos.value = true;
  try {
    availableRepos.value = await githubApi.listAvailableRepos(props.projectId);
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to list GitHub repositories'));
    availableRepos.value = [];
  } finally {
    loadingRepos.value = false;
  }
}

async function loadActivity() {
  loadingActivity.value = true;
  try {
    activity.value = await githubApi.getActivity(props.projectId);
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to load GitHub activity'));
    activity.value = null;
  } finally {
    loadingActivity.value = false;
  }
}

async function load() {
  loading.value = true;
  try {
    await ensureOrg();
    const [installs, linked] = await Promise.all([
      githubApi.listInstallations(),
      githubApi.getLinkedRepos(props.projectId)
    ]);
    installations.value = installs;
    linkedRepos.value = linked;
    selectedRepoIds.value = linked.map((repo) => repo.repo_id);
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to load GitHub integration'));
  } finally {
    loading.value = false;
  }
  if (hasInstallations.value) {
    void loadAvailableRepos();
  }
  if (linkedRepos.value.length) {
    void loadActivity();
  }
}

async function saveLinks() {
  saving.value = true;
  try {
    linkedRepos.value = await githubApi.setLinkedRepos(props.projectId, selectedRepoIds.value);
    selectedRepoIds.value = linkedRepos.value.map((repo) => repo.repo_id);
    showSuccess(
      linkedRepos.value.length
        ? `Linked ${linkedRepos.value.length} repositor${linkedRepos.value.length === 1 ? 'y' : 'ies'}`
        : 'All repositories unlinked'
    );
    await loadActivity();
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to link repositories'));
  } finally {
    saving.value = false;
  }
}

async function sync() {
  syncing.value = true;
  lastSync.value = null;
  try {
    lastSync.value = await githubApi.syncProject(props.projectId);
    showSuccess(
      `Synced ${lastSync.value.pull_requests} pull requests and ${lastSync.value.commits} commits from ${lastSync.value.repos} repos`
    );
    linkedRepos.value = await githubApi.getLinkedRepos(props.projectId);
    await loadActivity();
  } catch (error) {
    showError(getErrorMessage(error, 'GitHub sync failed'));
  } finally {
    syncing.value = false;
  }
}

watch(
  () => props.projectId,
  () => void load()
);

onMounted(() => {
  void load();
});
</script>

<template>
  <UiParentCard title="GitHub Integration">
    <v-progress-linear v-if="loading" indeterminate color="primary" class="mb-4" />

    <template v-else>
      <div v-if="!hasInstallations" class="d-flex flex-column ga-3">
        <v-alert type="info" variant="tonal">
          <template v-if="orgPermissions.canConnectGithub">
            Install the Keystone GitHub App for your organization first, then return here to link
            repositories.
          </template>
          <template v-else>
            Ask an organization admin to connect GitHub under Organization settings. Once connected, you
            can link repositories here.
          </template>
        </v-alert>
        <div>
          <v-btn
            color="primary"
            variant="flat"
            :to="{ path: '/settings/organization', query: { section: 'github' } }"
          >
            Open organization settings
          </v-btn>
        </div>
      </div>

      <div v-else class="d-flex flex-column ga-6">
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">Linked repositories</v-card-title>
          <v-card-text>
            <p class="text-medium-emphasis mb-4">
              A project can link several repositories, for example a frontend and a backend.
            </p>
            <v-autocomplete
              v-model="selectedRepoIds"
              :items="repoItems"
              :loading="loadingRepos"
              item-props
              label="Repositories"
              variant="outlined"
              density="comfortable"
              multiple
              chips
              closable-chips
              clearable
              hide-details="auto"
              no-data-text="No repositories available to the installed GitHub App"
            />

            <v-list v-if="linkedRepos.length" density="compact" class="mt-4 pa-0">
              <v-list-item v-for="repo in linkedRepos" :key="repo.id" class="px-0">
                <v-list-item-title>
                  <a v-if="repo.html_url" :href="repo.html_url" target="_blank" rel="noopener">
                    {{ repo.full_name }}
                  </a>
                  <span v-else>{{ repo.full_name }}</span>
                </v-list-item-title>
                <v-list-item-subtitle>
                  {{ repo.default_branch || 'default branch unknown' }} · Last synced
                  {{ formatDate(repo.last_synced_at) }}
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn color="primary" variant="flat" :loading="saving" :disabled="!selectionChanged" @click="saveLinks">
              Save
            </v-btn>
          </v-card-actions>
        </v-card>

        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1">Sync from GitHub</v-card-title>
          <v-card-text>
            <p class="text-medium-emphasis mb-4">
              Pull the last 90 days of pull requests and default-branch commits. New activity arrives
              automatically through webhooks.
            </p>
            <v-btn color="primary" variant="flat" :loading="syncing" :disabled="!linkedRepos.length" @click="sync">
              Sync now
            </v-btn>
            <v-alert v-if="!linkedRepos.length" type="info" variant="tonal" class="mt-4" density="comfortable">
              Link at least one repository before syncing.
            </v-alert>

            <div v-if="lastSync" class="mt-4">
              <div class="text-subtitle-2 mb-2">Last sync</div>
              <div class="d-flex flex-wrap ga-2">
                <v-chip size="small" variant="tonal">Repos {{ lastSync.repos }}</v-chip>
                <v-chip size="small" variant="tonal">Pull requests {{ lastSync.pull_requests }}</v-chip>
                <v-chip size="small" variant="tonal">Commits {{ lastSync.commits }}</v-chip>
              </div>
              <v-alert
                v-if="lastSync.errors.length"
                type="warning"
                variant="tonal"
                class="mt-3"
                density="comfortable"
              >
                {{ lastSync.errors.length }} repo(s) failed. First: {{ lastSync.errors[0].repo }} —
                {{ lastSync.errors[0].message }}
              </v-alert>
            </div>
          </v-card-text>
        </v-card>

        <v-card v-if="linkedRepos.length" variant="outlined">
          <v-card-title class="text-subtitle-1">Recent pull requests</v-card-title>
          <v-card-text>
            <v-progress-linear v-if="loadingActivity" indeterminate color="primary" class="mb-4" />
            <v-alert
              v-else-if="!activity?.pull_requests.length"
              type="info"
              variant="tonal"
              density="comfortable"
            >
              No pull requests yet. Run a sync or wait for webhook events.
            </v-alert>
            <v-list v-else lines="two" class="pa-0">
              <v-list-item v-for="pr in activity.pull_requests" :key="pr.id" class="px-0">
                <v-list-item-title class="d-flex align-center flex-wrap ga-2">
                  <v-chip :color="prStatusColor(pr.status, pr.draft)" size="x-small" variant="tonal">
                    {{ pr.draft && pr.status === 'open' ? 'draft' : pr.status }}
                  </v-chip>
                  <a v-if="pr.url" :href="pr.url" target="_blank" rel="noopener">{{ pr.title }}</a>
                  <span v-else>{{ pr.title }}</span>
                  <v-chip v-for="key in pr.jira_keys" :key="key" size="x-small" color="primary" variant="outlined">
                    {{ key }}
                  </v-chip>
                </v-list-item-title>
                <v-list-item-subtitle>
                  {{ pr.repo_full_name }}<span v-if="pr.number">#{{ pr.number }}</span>
                  <span v-if="pr.author_login"> · {{ pr.author_login }}</span>
                  <span v-if="pr.github_updated_at"> · updated {{ formatDate(pr.github_updated_at) }}</span>
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </div>
    </template>
  </UiParentCard>
</template>
