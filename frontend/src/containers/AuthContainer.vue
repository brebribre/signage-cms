<script setup lang="ts">
/**
 * Sign in, and only sign in. There is no public signup: accounts are issued by a platform
 * admin (Admin → Accounts), who hands the owner their username and password.
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
  // You land on Overview: the fleet at a glance. A ?next= link still wins.
  router.push((route.query.next as string) || { name: 'now' })
}
</script>

<template>
  <form class="flex flex-col gap-4" @submit.prevent="onSubmit">
    <h1 class="text-2xl">Sign in</h1>

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

    <p class="text-center text-[13px] text-ink-muted">
      No account yet? Accounts are set up for you — get in touch and we'll create one.
    </p>
  </form>
</template>
