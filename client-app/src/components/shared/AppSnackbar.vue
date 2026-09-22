<script setup lang="ts">
import { useSnackbar } from '@/composables/useSnackbar';

const { visible, message, color } = useSnackbar();
</script>

<template>
  <v-snackbar v-model="visible" :color="color" location="top right" timeout="4000">
    {{ message }}
    <template #actions>
      <v-btn variant="text" @click="visible = false">Close</v-btn>
    </template>
  </v-snackbar>
</template>
