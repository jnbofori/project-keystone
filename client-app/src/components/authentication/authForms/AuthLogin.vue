<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useSnackbar } from '@/composables/useSnackbar';
import { getErrorMessage } from '@/utils/apiError';

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const { showSuccess, showError } = useSnackbar();

const formRef = ref();
const showPassword = ref(false);
const email = ref('');
const password = ref('');

const emailRules = [
  (v: string) => !!v || 'Email is required',
  (v: string) => /.+@.+\..+/.test(v) || 'Email must be valid'
];

const passwordRules = [
  (v: string) => !!v || 'Password is required',
  (v: string) => (v && v.length >= 8) || 'Password must be at least 8 characters'
];

async function handleSubmit() {
  const result = await formRef.value?.validate();
  if (!result?.valid) return;

  try {
    await auth.login(email.value, password.value);
    showSuccess('Signed in successfully');
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard/default';
    router.push(redirect);
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to sign in'));
  }
}
</script>

<template>
  <h5 class="text-center my-4 mb-8">Sign in with email</h5>
  <v-form ref="formRef" @submit.prevent="handleSubmit" class="mt-7 loginForm">
    <v-text-field
      v-model="email"
      :rules="emailRules"
      label="Email Address"
      type="email"
      class="mt-4 mb-4"
      required
      hide-details="auto"
    />
    <v-text-field
      v-model="password"
      :rules="passwordRules"
      label="Password"
      required
      hide-details="auto"
      :append-inner-icon="showPassword ? '$eye' : '$eyeOff'"
      :type="showPassword ? 'text' : 'password'"
      @click:append-inner="showPassword = !showPassword"
    />

    <v-btn
      color="secondary"
      block
      class="mt-4"
      variant="flat"
      size="large"
      type="submit"
      :loading="auth.loading"
    >
      Sign In
    </v-btn>
  </v-form>
  <div class="mt-5 text-right">
    <v-divider />
    <v-btn variant="plain" to="/authentication/register" class="mt-2 text-capitalize mr-n2">
      Don't have an account?
    </v-btn>
  </div>
</template>

<style lang="scss">
.loginForm {
  .v-text-field .v-field--active input {
    font-weight: 500;
  }
}
</style>
