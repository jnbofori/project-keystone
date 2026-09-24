<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import BaseBreadcrumb from '@/components/shared/BaseBreadcrumb.vue';
import UiParentCard from '@/components/shared/UiParentCard.vue';
import DocumentUpload from '@/components/projects/DocumentUpload.vue';
import DocumentList from '@/components/projects/DocumentList.vue';
import QueryPanel from '@/components/projects/QueryPanel.vue';
import QueryHistory from '@/components/projects/QueryHistory.vue';
import MemberFormDialog from '@/components/projects/MemberFormDialog.vue';
import JiraIntegrationPanel from '@/components/projects/JiraIntegrationPanel.vue';
import { useProjectsStore } from '@/stores/projects';
import { useProjectRole } from '@/composables/useProjectRole';
import { useDocumentPolling } from '@/composables/useDocumentPolling';
import { useSnackbar } from '@/composables/useSnackbar';
import { getErrorMessage } from '@/utils/apiError';
import { documentsApi, queriesApi } from '@/api';
import type { Document, Query } from '@/api/types';

const route = useRoute();
const router = useRouter();
const projectsStore = useProjectsStore();
const { showSuccess, showError } = useSnackbar();

const activeTab = ref('overview');
const documentsLoading = ref(false);
const queries = ref<Query[]>([]);
const queriesLoading = ref(false);
const showAddMemberDialog = ref(false);
const showDeleteDocumentDialog = ref(false);
const showRemoveMemberDialog = ref(false);
const selectedDocumentId = ref<string | null>(null);
const selectedMemberUserId = ref<string | null>(null);
const deletingDocument = ref(false);
const removingMember = ref(false);

const projectId = computed(() => String((route.params as { id?: string }).id ?? ''));

const project = computed(() => projectsStore.currentProject);
const permissions = computed(() => useProjectRole(project.value?.current_user_role));

const documents = computed({
  get: () => projectsStore.documents,
  set: (value: Document[]) => {
    projectsStore.documents = value;
  }
});

const readyDocumentCount = computed(() => documents.value.filter((doc) => doc.status === 'ready').length);
const canAskQuestions = computed(() => permissions.value.canQuery && readyDocumentCount.value > 0);

const pageTitle = computed(() => project.value?.name ?? 'Project');
const breadcrumbs = computed(() => [
  { title: 'Home', disabled: false, href: '/dashboard/default' },
  { title: 'Projects', disabled: false, href: '/projects' },
  { title: pageTitle.value, disabled: true, href: '#' }
]);

const memberHeaders = [
  { title: 'Email', key: 'email' },
  { title: 'Role', key: 'role' },
  { title: 'Joined', key: 'created_at' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' as const }
];

useDocumentPolling(projectId, documents);

function applyTabFromQuery() {
  const tab = route.query.tab;
  if (typeof tab === 'string' && tab) {
    if (tab === 'jira' && !permissions.value.canManageJira) {
      activeTab.value = 'overview';
      return;
    }
    if (tab === 'members' && !permissions.value.canManageMembers) {
      activeTab.value = 'overview';
      return;
    }
    activeTab.value = tab;
  }
}

async function loadProject() {
  await projectsStore.fetchProject(projectId.value);
}

async function loadDocuments() {
  documentsLoading.value = true;
  try {
    await projectsStore.fetchDocuments(projectId.value);
  } finally {
    documentsLoading.value = false;
  }
}

async function loadQueries() {
  if (!permissions.value.canViewQueryHistory) {
    queries.value = [];
    return;
  }

  queriesLoading.value = true;
  try {
    queries.value = await queriesApi.listQueries(projectId.value);
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to load query history'));
  } finally {
    queriesLoading.value = false;
  }
}

async function loadMembers() {
  if (!permissions.value.canManageMembers) return;
  await projectsStore.fetchMembers(projectId.value);
}

async function loadAll() {
  await loadProject();
  applyTabFromQuery();
  await Promise.all([loadDocuments(), loadQueries(), loadMembers()]);
}

function handleDocumentUploaded(document: Document) {
  documents.value = [document, ...documents.value];
}

function confirmDeleteDocument(documentId: string) {
  selectedDocumentId.value = documentId;
  showDeleteDocumentDialog.value = true;
}

async function deleteDocument() {
  if (!selectedDocumentId.value) return;

  deletingDocument.value = true;
  try {
    await documentsApi.deleteDocument(projectId.value, selectedDocumentId.value);
    documents.value = documents.value.filter((doc) => doc.id !== selectedDocumentId.value);
    showSuccess('Document deleted');
    showDeleteDocumentDialog.value = false;
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to delete document'));
  } finally {
    deletingDocument.value = false;
  }
}

function confirmRemoveMember(userId: string) {
  selectedMemberUserId.value = userId;
  showRemoveMemberDialog.value = true;
}

async function removeMember() {
  if (!selectedMemberUserId.value) return;

  removingMember.value = true;
  try {
    await projectsStore.removeMember(projectId.value, selectedMemberUserId.value);
    showSuccess('Member removed');
    showRemoveMemberDialog.value = false;
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to remove member'));
  } finally {
    removingMember.value = false;
  }
}

function handleQueryAsked(query: Query) {
  queries.value = [query, ...queries.value];
}

async function handleJiraLinked(jiraProjectKey: string | null) {
  await projectsStore.fetchProject(projectId.value);
  if (projectsStore.currentProject && jiraProjectKey === null) {
    projectsStore.currentProject = {
      ...projectsStore.currentProject,
      jira_project_key: null,
      jira_project_id: null
    };
  }
}

function onTabChange(tab: unknown) {
  const value = String(tab ?? 'overview');
  activeTab.value = value;
  const query = { ...route.query } as Record<string, string | string[] | undefined>;
  if (value === 'overview') {
    delete query.tab;
  } else {
    query.tab = value;
  }
  void router.replace({ query });
}

onMounted(loadAll);

watch(projectId, loadAll);
watch(
  () => route.query.tab,
  () => applyTabFromQuery()
);
</script>

<template>
  <BaseBreadcrumb :title="pageTitle" :breadcrumbs="breadcrumbs" />

  <v-progress-linear v-if="projectsStore.loading && !project" indeterminate color="primary" class="mb-4" />

  <template v-if="project">
    <UiParentCard :title="project.name">
      <div class="d-flex flex-wrap align-center ga-3 mb-2">
        <v-chip color="primary" variant="tonal">{{ project.current_user_role }}</v-chip>
        <span class="text-medium-emphasis">{{ project.description || 'No description provided.' }}</span>
      </div>
    </UiParentCard>

    <v-tabs v-model="activeTab" color="primary" class="mt-4" show-arrows @update:model-value="onTabChange">
      <v-tab value="overview">Overview</v-tab>
      <v-tab v-if="permissions.canManageJira" value="jira">Jira</v-tab>
      <v-tab v-if="permissions.canManageMembers" value="members">Members</v-tab>
      <v-tab value="documents">Documents</v-tab>
      <v-tab value="ask">Ask</v-tab>
    </v-tabs>

    <v-window v-model="activeTab" class="mt-4">
      <v-window-item value="overview">
        <v-row>
          <v-col cols="12" sm="4">
            <v-card variant="outlined">
              <v-card-text>
                <div class="text-body-small text-medium-emphasis">Documents</div>
                <div class="text-h4">{{ documents.length }}</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" sm="4">
            <v-card variant="outlined">
              <v-card-text>
                <div class="text-body-small text-medium-emphasis">Ready</div>
                <div class="text-h4">{{ readyDocumentCount }}</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" sm="4">
            <v-card variant="outlined">
              <v-card-text>
                <div class="text-body-small text-medium-emphasis">Questions</div>
                <div class="text-h4">{{ queries.length }}</div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
        <v-alert type="info" variant="tonal" class="mt-4">
          Use <strong>Jira</strong> and <strong>Members</strong> for delivery. Documents and Ask are
          knowledge features for this project.
        </v-alert>
      </v-window-item>

      <v-window-item v-if="permissions.canManageJira" value="jira">
        <JiraIntegrationPanel
          :project-id="projectId"
          :linked-jira-key="project?.jira_project_key"
          @linked="handleJiraLinked"
        />
      </v-window-item>

      <v-window-item v-if="permissions.canManageMembers" value="members">
        <UiParentCard title="Project Members">
          <template #action>
            <v-btn color="primary" variant="flat" @click="showAddMemberDialog = true">Add Member</v-btn>
          </template>

          <v-data-table
            :headers="memberHeaders"
            :items="projectsStore.members"
            item-value="id"
            density="comfortable"
          >
            <template #item.role="{ item }">
              <v-chip size="small" variant="tonal">{{ item.role }}</v-chip>
            </template>
            <template #item.created_at="{ item }">
              {{ new Date(item.created_at).toLocaleDateString() }}
            </template>
            <template #item.actions="{ item }">
              <v-btn
                v-if="item.role !== 'owner'"
                size="small"
                color="error"
                variant="text"
                @click="confirmRemoveMember(item.user_id)"
              >
                Remove
              </v-btn>
            </template>
            <template #no-data>
              <v-alert type="info" variant="tonal" class="ma-4">No members found.</v-alert>
            </template>
          </v-data-table>
        </UiParentCard>
      </v-window-item>

      <v-window-item value="documents">
        <v-alert type="info" variant="tonal" class="mb-4" density="comfortable">
          Knowledge — upload sources for Ask.
        </v-alert>
        <DocumentUpload
          v-if="permissions.canUpload"
          :project-id="projectId"
          class="mb-4"
          @uploaded="handleDocumentUploaded"
        />
        <v-alert v-else type="info" variant="tonal" class="mb-4">
          You have viewer access and cannot upload documents.
        </v-alert>

        <DocumentList
          :documents="documents"
          :loading="documentsLoading"
          :can-delete="permissions.canDeleteDocuments"
          @delete="confirmDeleteDocument"
        />
      </v-window-item>

      <v-window-item value="ask">
        <v-alert type="info" variant="tonal" class="mb-4" density="comfortable">
          Knowledge — ask questions against this project’s documents.
        </v-alert>
        <QueryHistory :queries="queries" :loading="queriesLoading" class="mb-4" />
        <QueryPanel
          :project-id="projectId"
          :disabled="!canAskQuestions"
          :disabled-message="
            readyDocumentCount === 0
              ? 'Upload documents and wait until at least one is ready before asking questions.'
              : 'You do not have permission to ask questions in this project.'
          "
          @asked="handleQueryAsked"
        />
      </v-window-item>
    </v-window>
  </template>

  <MemberFormDialog
    v-model="showAddMemberDialog"
    :project-id="projectId"
    @added="loadMembers"
  />

  <v-dialog v-model="showDeleteDocumentDialog" max-width="420">
    <v-card>
      <v-card-title>Delete document?</v-card-title>
      <v-card-text>This action cannot be undone.</v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="showDeleteDocumentDialog = false">Cancel</v-btn>
        <v-btn color="error" variant="flat" :loading="deletingDocument" @click="deleteDocument">Delete</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-dialog v-model="showRemoveMemberDialog" max-width="420">
    <v-card>
      <v-card-title>Remove member?</v-card-title>
      <v-card-text>This user will lose access to the project.</v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="showRemoveMemberDialog = false">Cancel</v-btn>
        <v-btn color="error" variant="flat" :loading="removingMember" @click="removeMember">Remove</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
