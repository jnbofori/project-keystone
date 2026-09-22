<script setup lang="ts">
import { ref, watch } from 'vue';
import { useProjectsStore } from '@/stores/projects';
import { useSnackbar } from '@/composables/useSnackbar';
import { getErrorMessage } from '@/utils/apiError';

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  created: [projectId: string];
}>();

const projectsStore = useProjectsStore();
const { showSuccess, showError } = useSnackbar();

const formRef = ref();
const name = ref('');
const description = ref('');
const saving = ref(false);

const nameRules = [(v: string) => !!v?.trim() || 'Project name is required'];

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      name.value = '';
      description.value = '';
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
    const project = await projectsStore.createProject({
      name: name.value.trim(),
      description: description.value.trim() || null
    });
    showSuccess('Project created');
    emit('created', project.id);
    close();
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to create project'));
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <v-dialog :model-value="modelValue" max-width="520" @update:model-value="emit('update:modelValue', $event)">
    <v-card>
      <v-card-title>Create Project</v-card-title>
      <v-card-text>
        <v-form ref="formRef" @submit.prevent="handleSubmit">
          <v-text-field v-model="name" label="Project name" :rules="nameRules" required hide-details="auto" class="mb-4" />
          <v-textarea v-model="description" label="Description (optional)" rows="3" hide-details="auto" />
        </v-form>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="close">Cancel</v-btn>
        <v-btn color="primary" variant="flat" :loading="saving" @click="handleSubmit">Create</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
