<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppInput from '@/reusables/AppInput.vue'

const props = defineProps<{ mode: 'login' | 'signup' }>()

const router = useRouter()
const route = useRoute()
const { login, signup, isLoading, error } = useAuth()

const identifier = ref('')
const password = ref('')
const username = ref('')
const displayName = ref('')
const accountName = ref('')

async function onSubmit() {
  const ok =
    props.mode === 'login'
      ? await login({ identifier: identifier.value, password: password.value })
      : await signup({
          username: username.value,
          password: password.value,
          display_name: displayName.value,
          account_name: accountName.value || null,
        })
  if (ok) router.push((route.query.next as string) || { name: 'media' })
}
</script>

<template>
  <form class="flex flex-col gap-4" @submit.prevent="onSubmit">
    <h1 class="text-2xl">{{ mode === 'login' ? 'Sign in' : 'Create an account' }}</h1>

    <template v-if="mode === 'login'">
      <AppInput
        id="identifier"
        v-model="identifier"
        label="Username or email"
        autocomplete="username"
        required
      />
    </template>
    <template v-else>
      <AppInput
        id="username"
        v-model="username"
        label="Username"
        autocomplete="username"
        hint="3–32 characters: letters, digits, dot, underscore, hyphen"
        required
      />
      <AppInput id="display-name" v-model="displayName" label="Your name" required />
      <AppInput
        id="account-name"
        v-model="accountName"
        label="Account name"
        hint="Optional — the organisation these screens belong to"
      />
    </template>

    <AppInput
      id="password"
      v-model="password"
      label="Password"
      type="password"
      :autocomplete="mode === 'login' ? 'current-password' : 'new-password'"
      :hint="mode === 'signup' ? 'At least 8 characters' : undefined"
      required
    />

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>

    <AppButton type="submit" block :loading="isLoading">
      {{ mode === 'login' ? 'Sign in' : 'Create account' }}
    </AppButton>

    <p class="text-center text-[13px] text-ink-muted">
      <template v-if="mode === 'login'">
        No account?
        <router-link class="text-ink underline underline-offset-2" :to="{ name: 'signup' }">
          Create one
        </router-link>
      </template>
      <template v-else>
        Already have one?
        <router-link class="text-ink underline underline-offset-2" :to="{ name: 'login' }">
          Sign in
        </router-link>
      </template>
    </p>
  </form>
</template>
