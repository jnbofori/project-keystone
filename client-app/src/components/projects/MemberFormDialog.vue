<script setup lang="ts">
import { ref, watch } from 'vue';
import type { ProjectRole } from '@/api/types';
import { useProjectsStore } from '@/stores/projects';
import { useSnackbar } from '@/composables/useSnackbar';
import { getErrorMessage } from '@/utils/apiError';

const props = defineProps<{
  modelValue: boolean;
  projectId: string;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  added: [];
}>();

const projectsStore = useProjectsStore();
const { showSuccess, showError } = useSnackbar();

const formRef = ref();
const email = ref('');
const role = ref<ProjectRole>('member');
const saving = ref(false);

const roleOptions: ProjectRole[] = ['viewer', 'member', 'admin'];

const emailRules = [
  (v: string) => !!v || 'Email is required',
  (v: string) => /.+@.+\..+/.test(v) || 'Email must be valid'
];

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      email.value = '';
      role.value = 'member';
      formRef.value?.resetValidation?.();
    }
  }
);

function close() {
  emit('update:modelValue', false);
}

async function handleSubmit() {
  const result = await formRef.value?.validate();
  if (!result?.valid) return;

  saving.value = true;
  try {
    await projectsStore.addMember(props.projectId, {
      email: email.value.trim(),
      role: role.value
    });
    showSuccess('Member added');
    emit('added');
    close();
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to add member'));
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <v-dialog :model-value="modelValue" max-width="520" @update:model-value="emit('update:modelValue', $event)">
    <v-card>
      <v-card-title>Add Member</v-card-title>
      <v-card-text>
        <v-form ref="formRef" @submit.prevent="handleSubmit">
          <v-text-field v-model="email" label="User email" :rules="emailRules" required hide-details="auto" class="mb-4" />
          <v-select
            v-model="role"
            :items="roleOptions"
            label="Role"
            hide-details="auto"
          />
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="close">Cancel</v-btn>
        <v-btn color="primary" variant="flat" :loading="saving" @click="handleSubmit">Add</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
