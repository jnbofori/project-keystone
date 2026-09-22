<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  text: string;
}>();

const formattedHtml = computed(() => {
  const normalized = props.text.replace(/\\n/g, '\n');

  const escaped = normalized
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  return escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
});
</script>

<template>
  <div class="formatted-answer" v-html="formattedHtml" />
</template>

<style scoped>
.formatted-answer {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.6;
}
</style>
