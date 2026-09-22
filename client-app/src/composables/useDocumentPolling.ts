import { onUnmounted, ref, watch, type Ref } from 'vue';
import type { Document } from '@/api/types';
import { documentsApi } from '@/api';

const POLL_INTERVAL_MS = 3000;
const ACTIVE_STATUSES = new Set(['pending', 'processing']);

export function useDocumentPolling(projectId: Ref<string>, documents: Ref<Document[]>, onUpdate?: () => void) {
  const polling = ref(false);
  let timer: ReturnType<typeof setInterval> | null = null;

  async function refreshDocuments() {
    documents.value = await documentsApi.listDocuments(projectId.value);
    onUpdate?.();
  }

  function stopPolling() {
    polling.value = false;
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  }

  function startPolling() {
    if (timer) return;
    polling.value = true;
    timer = setInterval(async () => {
      await refreshDocuments();
      const hasActive = documents.value.some((doc) => ACTIVE_STATUSES.has(doc.status));
      if (!hasActive) {
        stopPolling();
      }
    }, POLL_INTERVAL_MS);
  }

  watch(
    documents,
    (docs) => {
      const hasActive = docs.some((doc) => ACTIVE_STATUSES.has(doc.status));
      if (hasActive) {
        startPolling();
      } else {
        stopPolling();
      }
    },
    { deep: true, immediate: true }
  );

  onUnmounted(stopPolling);

  return {
    polling,
    refreshDocuments,
    stopPolling
  };
}
