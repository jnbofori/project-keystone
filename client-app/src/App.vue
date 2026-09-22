<template>
  <RouterView></RouterView>
  <AppSnackbar />
</template>

<script setup lang="ts">
import { RouterView } from 'vue-router';
import AppSnackbar from '@/components/shared/AppSnackbar.vue';
</script>
