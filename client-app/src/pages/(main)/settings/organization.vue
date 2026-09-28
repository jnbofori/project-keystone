<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import BaseBreadcrumb from '@/components/shared/BaseBreadcrumb.vue';
import UiParentCard from '@/components/shared/UiParentCard.vue';
import { githubApi, jiraApi } from '@/api';
import type { GithubInstallation, JiraConnection, OrganizationRole } from '@/api/types';
import { useOrgRole } from '@/composables/useOrgRole';
import { useSnackbar } from '@/composables/useSnackbar';
import { useAuthStore } from '@/stores/auth';
import { useOrganizationStore } from '@/stores/organization';
import { getErrorMessage } from '@/utils/apiError';

const route = useRoute();
const auth = useAuthStore();
const orgStore = useOrganizationStore();
const { showSuccess, showError } = useSnackbar();

const jiraSection = ref<HTMLElement | null>(null);
const connection = ref<JiraConnection | null>(null);
const selectedCloudId = ref<string | null>(null);
const jiraLoading = ref(false);
const connecting = ref(false);
const disconnecting = ref(false);
const selectingCloud = ref(false);
const rotating = ref(false);
const copying = ref(false);

const githubSection = ref<HTMLElement | null>(null);
const githubInstallations = ref<GithubInstallation[]>([]);
const githubLoading = ref(false);
const githubInstalling = ref(false);
const githubRemovingId = ref<string | null>(null);

const orgPermissions = computed(() => useOrgRole(orgStore.currentRole));
const connected = computed(() => Boolean(connection.value?.connected));
const needsSite = computed(() => Boolean(connection.value?.needs_site_selection));
const siteOptions = computed(() => connection.value?.available_sites ?? []);

const breadcrumbs = [
  { title: 'Home', disabled: false, href: '/dashboard/default' },
  { title: 'Organization', disabled: true, href: '#' }
];

const memberHeaders = [
  { title: 'Email', key: 'email' },
  { title: 'Role', key: 'role' },
  { title: 'Joined', key: 'created_at' }
];

const roleOptions: OrganizationRole[] = ['member', 'admin', 'owner'];

async function loadOrganization() {
  try {
    await orgStore.fetchMe();
    await orgStore.fetchMembers();
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to load organization'));
  }
}

async function loadJiraConnection() {
  if (!orgPermissions.value.canConnectJira) {
    connection.value = null;
    return;
  }
  jiraLoading.value = true;
  try {
    connection.value = await jiraApi.getConnection();
    selectedCloudId.value = connection.value.cloud_id;
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to load Jira connection'));
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
  } finally {
    jiraLoading.value = false;
  }
}

async function connectJira() {
  connecting.value = true;
  try {
    const { authorize_url } = await jiraApi.startOAuth();
    window.location.href = authorize_url;
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to start Jira OAuth'));
    connecting.value = false;
  }
}

async function disconnectJira() {
  disconnecting.value = true;
  try {
    await jiraApi.disconnect();
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
    showSuccess('Jira disconnected for this organization');
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
    connection.value = await jiraApi.selectCloud(selectedCloudId.value);
    showSuccess('Atlassian site selected');
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to select Atlassian site'));
  } finally {
    selectingCloud.value = false;
  }
}

async function loadGithubInstallations() {
  githubLoading.value = true;
  try {
    githubInstallations.value = await githubApi.listInstallations();
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to load GitHub installations'));
    githubInstallations.value = [];
  } finally {
    githubLoading.value = false;
  }
}

async function installGithub() {
  githubInstalling.value = true;
  try {
    const { install_url } = await githubApi.startInstall();
    window.location.href = install_url;
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to start GitHub App installation'));
    githubInstalling.value = false;
  }
}

async function removeGithubInstallation(installation: GithubInstallation) {
  githubRemovingId.value = installation.id;
  try {
    await githubApi.removeInstallation(installation.id);
    githubInstallations.value = githubInstallations.value.filter((i) => i.id !== installation.id);
    showSuccess(`GitHub account ${installation.account_login} removed`);
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to remove GitHub installation'));
  } finally {
    githubRemovingId.value = null;
  }
}

async function rotateInvite() {
  rotating.value = true;
  try {
    await orgStore.rotateInviteCode();
    showSuccess('Invite code rotated');
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to rotate invite code'));
  } finally {
    rotating.value = false;
  }
}

async function copyInviteCode() {
  const code = orgStore.organization?.invite_code;
  if (!code) return;
  copying.value = true;
  try {
    await navigator.clipboard.writeText(code);
    showSuccess('Invite code copied');
  } catch {
    showError('Could not copy invite code');
  } finally {
    copying.value = false;
  }
}

async function changeMemberRole(userId: string, role: OrganizationRole) {
  try {
    await orgStore.updateMemberRole(userId, role);
    showSuccess('Member role updated');
    if (userId === auth.user?.id) {
      await orgStore.fetchMe();
    }
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to update member role'));
    await orgStore.fetchMembers();
  }
}

function scrollToSectionIfNeeded() {
  if (route.query.section === 'jira' || route.hash === '#jira') {
    jiraSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } else if (route.query.section === 'github' || route.hash === '#github') {
    githubSection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

onMounted(async () => {
  await loadOrganization();
  await Promise.all([loadJiraConnection(), loadGithubInstallations()]);
  scrollToSectionIfNeeded();
});

watch(
  () => route.query.section,
  () => scrollToSectionIfNeeded()
);
</script>

<template>
  <BaseBreadcrumb title="Organization" :breadcrumbs="breadcrumbs" />

  <v-progress-linear v-if="orgStore.loading && !orgStore.organization" indeterminate color="primary" class="mb-4" />

  <template v-if="orgStore.organization">
    <UiParentCard :title="orgStore.organization.name">
      <div class="d-flex flex-wrap align-center ga-3">
        <v-chip color="primary" variant="tonal">{{ orgStore.organization.current_user_role }}</v-chip>
        <span class="text-medium-emphasis">
          One Atlassian site and invite code for everyone in this organization.
        </span>
      </div>
    </UiParentCard>

    <UiParentCard v-if="orgPermissions.canRotateInvite" title="Invite code" class="mt-4">
      <p class="text-medium-emphasis mb-4">
        Share this code so teammates can join your organization when they register. Only organization
        members can be added to projects.
      </p>
      <div class="d-flex flex-wrap align-center ga-3">
        <v-text-field
          :model-value="orgStore.organization.invite_code || ''"
          label="Invite code"
          readonly
          variant="outlined"
          density="comfortable"
          hide-details
          class="flex-grow-1"
          style="max-width: 420px"
        />
        <v-btn variant="tonal" :loading="copying" @click="copyInviteCode">Copy</v-btn>
        <v-btn color="primary" variant="flat" :loading="rotating" @click="rotateInvite">
          Rotate code
        </v-btn>
      </div>
    </UiParentCard>

    <UiParentCard title="Members" class="mt-4">
      <v-data-table
        :headers="memberHeaders"
        :items="orgStore.members"
        :loading="orgStore.membersLoading"
        item-value="id"
        density="comfortable"
      >
        <template #item.role="{ item }">
          <v-select
            v-if="orgPermissions.canChangeMemberRoles"
            :model-value="item.role"
            :items="roleOptions"
            density="compact"
            variant="outlined"
            hide-details
            style="max-width: 140px"
            @update:model-value="(value) => changeMemberRole(item.user_id, value as OrganizationRole)"
          />
          <v-chip v-else size="small" variant="tonal">{{ item.role }}</v-chip>
        </template>
        <template #item.created_at="{ item }">
          {{ new Date(item.created_at).toLocaleDateString() }}
        </template>
        <template #no-data>
          <v-alert type="info" variant="tonal" class="ma-4">No members found.</v-alert>
        </template>
      </v-data-table>
    </UiParentCard>

    <div ref="jiraSection" id="jira">
      <UiParentCard title="Jira connection" class="mt-4">
        <template v-if="!orgPermissions.canConnectJira">
          <v-alert type="info" variant="tonal">
            Only organization owners and admins can connect Jira. Ask an admin to connect Atlassian,
            then link a Jira project from any Keystone project.
          </v-alert>
        </template>

        <template v-else>
          <v-progress-linear v-if="jiraLoading" indeterminate color="primary" class="mb-4" />

          <div v-else-if="!connected" class="d-flex flex-column ga-3">
            <p class="text-medium-emphasis mb-0">
              Connect Jira once for the organization. Projects then link individual Jira project keys
              and sync delivery data.
            </p>
            <div>
              <v-btn color="primary" variant="flat" :loading="connecting" @click="connectJira">
                Connect to Jira
              </v-btn>
            </div>
          </div>

          <div v-else class="d-flex flex-column ga-6">
            <div class="d-flex flex-wrap align-center justify-space-between ga-3">
              <div>
                <div class="d-flex align-center ga-2 mb-1">
                  <v-chip color="success" variant="tonal" size="small">Connected</v-chip>
                  <span v-if="connection?.site_name" class="font-weight-medium">
                    {{ connection.site_name }}
                  </span>
                </div>
                <div v-if="connection?.site_url" class="text-body-2 text-medium-emphasis">
                  {{ connection.site_url }}
                </div>
              </div>
              <v-btn color="error" variant="tonal" :loading="disconnecting" @click="disconnectJira">
                Disconnect
              </v-btn>
            </div>

            <v-card v-if="needsSite" variant="outlined">
              <v-card-title class="text-subtitle-1">Select Atlassian site</v-card-title>
              <v-card-text>
                <v-select
                  v-model="selectedCloudId"
                  :items="siteOptions"
                  :item-title="
                    (item: { site_name: string | null; site_url: string | null }) =>
                      item.site_name || item.site_url || 'Site'
                  "
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

            <v-alert v-else type="success" variant="tonal">
              Organization Jira is ready. Open a project’s Jira tab to link a project key and sync.
            </v-alert>
          </div>
        </template>
      </UiParentCard>
    </div>

    <div ref="githubSection" id="github">
      <UiParentCard title="GitHub" class="mt-4">
        <p class="text-medium-emphasis mb-4">
          Install the Keystone GitHub App on one or more GitHub accounts or organizations. Projects can
          then link any of the repositories you grant access to.
        </p>

        <v-alert v-if="!orgPermissions.canConnectGithub" type="info" variant="tonal" class="mb-4">
          Only organization owners and admins can connect GitHub accounts.
        </v-alert>

        <v-progress-linear v-if="githubLoading" indeterminate color="primary" class="mb-4" />

        <v-list v-else-if="githubInstallations.length" lines="two" class="mb-4 pa-0">
          <v-list-item v-for="installation in githubInstallations" :key="installation.id" class="px-0">
            <template #prepend>
              <v-avatar size="36" class="mr-3">
                <v-img v-if="installation.account_avatar_url" :src="installation.account_avatar_url" />
                <v-icon v-else icon="$github" />
              </v-avatar>
            </template>
            <v-list-item-title class="d-flex align-center ga-2">
              {{ installation.account_login }}
              <v-chip v-if="installation.suspended_at" color="warning" size="x-small" variant="tonal">
                Suspended
              </v-chip>
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ installation.account_type || 'Account' }} ·
              {{ installation.repository_selection === 'all' ? 'All repositories' : 'Selected repositories' }}
            </v-list-item-subtitle>
            <template v-if="orgPermissions.canConnectGithub" #append>
              <v-btn
                color="error"
                variant="text"
                size="small"
                :loading="githubRemovingId === installation.id"
                @click="removeGithubInstallation(installation)"
              >
                Remove
              </v-btn>
            </template>
          </v-list-item>
        </v-list>

        <v-alert v-else type="info" variant="tonal" class="mb-4">No GitHub accounts connected yet.</v-alert>

        <v-btn
          v-if="orgPermissions.canConnectGithub"
          color="primary"
          variant="flat"
          prepend-icon="$github"
          :loading="githubInstalling"
          @click="installGithub"
        >
          {{ githubInstallations.length ? 'Add GitHub account' : 'Install GitHub App' }}
        </v-btn>
      </UiParentCard>
    </div>
  </template>
</template>
