<script setup lang="ts">
/**
 * Sign in to the monitoring console. Same username and password as the CMS, but the server
 * only lets a platform admin through — anyone else gets "Invalid username or password", the
 * same words a wrong password gets, so there is nothing to learn from trying.
 */
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppInput from '@/reusables/AppInput.vue'

const router = useRouter()
const route = useRoute()
const { login, isLoading, error } = useAuth()

const identifier = ref('')
const password = ref('')

async function onSubmit() {
  if (!(await login({ identifier: identifier.value, password: password.value }))) return
  // A ?next= link still wins; otherwise the first page.
  router.push((route.query.next as string) || { name: 'accounts' })
}
</script>

<template>
  <form class="flex flex-col gap-4" @submit.prevent="onSubmit">
    <div>
      <h1 class="text-2xl">Sign in</h1>
      <p class="mt-1 text-sm text-ink-muted">Monitoring — Paskall staff only.</p>
    </div>

    <AppInput
      id="identifier"
      v-model="identifier"
      label="Username or email"
      autocomplete="username"
      required
    />
    <AppInput
      id="password"
      v-model="password"
      label="Password"
      type="password"
      autocomplete="current-password"
      required
    />

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>

    <AppButton type="submit" block :loading="isLoading">Sign in</AppButton>
  </form>
</template>
