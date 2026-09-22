import { ref } from 'vue';

type SnackbarColor = 'success' | 'error' | 'info' | 'warning';

const visible = ref(false);
const message = ref('');
const color = ref<SnackbarColor>('info');

function show(text: string, snackbarColor: SnackbarColor = 'info') {
  message.value = text;
  color.value = snackbarColor;
  visible.value = true;
}

export function useSnackbar() {
  return {
    visible,
    message,
    color,
    showSuccess: (text: string) => show(text, 'success'),
    showError: (text: string) => show(text, 'error'),
    showInfo: (text: string) => show(text, 'info'),
    showWarning: (text: string) => show(text, 'warning')
  };
}
