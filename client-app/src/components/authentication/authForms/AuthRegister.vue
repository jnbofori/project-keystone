<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useSnackbar } from '@/composables/useSnackbar';
import { getErrorMessage } from '@/utils/apiError';

const router = useRouter();
const auth = useAuthStore();
const { showSuccess, showError } = useSnackbar();

type JoinMode = 'create' | 'join';

const formRef = ref();
const showPassword = ref(false);
const email = ref('');
const password = ref('');
const joinMode = ref<JoinMode>('create');
const organizationName = ref('');
const inviteCode = ref('');
const agreeTerms = ref(false);

const emailRules = [
  (v: string) => !!v || 'Email is required',
  (v: string) => /.+@.+\..+/.test(v) || 'Email must be valid'
];

const passwordRules = [
  (v: string) => !!v || 'Password is required',
  (v: string) => (v && v.length >= 8) || 'Password must be at least 8 characters'
];

const organizationNameRules = computed(() =>
  joinMode.value === 'create'
    ? [
        (v: string) => !!v?.trim() || 'Organization name is required',
        (v: string) => (v?.trim().length ?? 0) <= 255 || 'Name is too long'
      ]
    : []
);

const inviteCodeRules = computed(() =>
  joinMode.value === 'join' ? [(v: string) => !!v?.trim() || 'Invite code is required'] : []
);

async function handleSubmit() {
  const result = await formRef.value?.validate();
  if (!result?.valid) return;

  try {
    await auth.register({
      email: email.value.trim(),
      password: password.value,
      ...(joinMode.value === 'create'
        ? { organization_name: organizationName.value.trim() }
        : { invite_code: inviteCode.value.trim() })
    });
    showSuccess('Account created successfully');
    router.push('/dashboard/default');
  } catch (error) {
    showError(getErrorMessage(error, 'Failed to create account'));
  }
}
</script>

<template>
  <h5 class="text-center my-4 mb-8">Sign up with email</h5>
  <v-form ref="formRef" class="mt-7 loginForm" @submit.prevent="handleSubmit">
    <v-btn-toggle
      v-model="joinMode"
      class="mb-4 w-100"
      color="primary"
      density="comfortable"
      mandatory
      divided
    >
      <v-btn value="create" class="flex-grow-1 text-none">Create organization</v-btn>
      <v-btn value="join" class="flex-grow-1 text-none">Join with invite code</v-btn>
    </v-btn-toggle>

    <v-text-field
      v-if="joinMode === 'create'"
      v-model="organizationName"
      :rules="organizationNameRules"
      label="Organization name"
      class="mb-4"
      required
      hide-details="auto"
    />
    <v-text-field
      v-else
      v-model="inviteCode"
      :rules="inviteCodeRules"
      label="Invite code"
      class="mb-4"
      required
      hide-details="auto"
      hint="Ask an organization admin for the invite code"
      persistent-hint
    />

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

    <div class="d-sm-inline-flex align-center mt-2 mb-4 font-weight-bold">
      <v-checkbox
        v-model="agreeTerms"
        :rules="[(v: boolean) => !!v || 'You must agree to continue']"
        label="Agree to terms"
        required
        color="primary"
        class="ms-n2"
        hide-details
      />
    </div>

    <v-btn
      color="secondary"
      block
      class="mt-2"
      variant="flat"
      size="large"
      type="submit"
      :loading="auth.loading"
    >
      Sign Up
    </v-btn>
  </v-form>
  <div class="mt-5 text-right">
    <v-divider />
    <v-btn variant="plain" to="/authentication/login" class="mt-2 text-capitalize mr-n2">
      Already have an account?
    </v-btn>
  </div>
</template>
