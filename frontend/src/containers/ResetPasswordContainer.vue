<script setup lang="ts">
/**
 * Reset password, reached from the sign-in page — for someone who isn't signed in.
 *
 * There is no email, so nobody can reset a password they've lost on their own. What this page
 * can do is let someone who knows their current password — often the temporary one they were
 * given — replace it in one step, without signing in first: it signs in with it, then changes it
 * (the same two calls the sign-in page and Choose your own password make). For a password that's
 * really forgotten, it says who can reset it: Marien for an account's main user, the main user
 * for a sub account (see ACCOUNTS.md, "Passwords").
 */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppInput from '@/reusables/AppInput.vue'

const router = useRouter()
const { login, changePassword, isLoading, error } = useAuth()

const identifier = ref('')
const current = ref('')
const next = ref('')
const confirm = ref('')

/** Said before the server has to: the same rules it enforces. */
const problem = computed(() => {
  if (next.value && next.value.length < 8) return 'At least 8 characters.'
  if (confirm.value && confirm.value !== next.value) return "The two new passwords don't match."
  if (next.value && next.value === current.value) return 'Choose something different from the current one.'
  return null
})
const ready = computed(
  () => identifier.value.trim() && current.value && next.value.length >= 8 && confirm.value === next.value && !problem.value,
)

async function onSubmit() {
  if (!ready.value) return
  if (!(await login({ identifier: identifier.value.trim(), password: current.value }))) return
  if (!(await changePassword(current.value, next.value))) return
  router.push({ name: 'now' })
}
</script>

<template>
  <form class="flex flex-col gap-4" @submit.prevent="onSubmit">
    <h1 class="text-2xl">Reset password</h1>
    <p class="text-[13px] text-ink-muted">
      Replace your password with one only you know — including a temporary one you were given.
    </p>

    <AppInput id="reset-identifier" v-model="identifier" label="Username or email" autocomplete="username" required />
    <AppInput
      id="reset-current" v-model="current" type="password" required autocomplete="current-password"
      label="Current or temporary password"
    />
    <AppInput
      id="reset-new" v-model="next" type="password" required autocomplete="new-password"
      label="New password" hint="At least 8 characters."
    />
    <AppInput id="reset-confirm" v-model="confirm" type="password" required autocomplete="new-password" label="New password again" />

    <AppAlert v-if="problem" tone="danger">{{ problem }}</AppAlert>
    <AppAlert v-else-if="error" tone="danger">{{ error }}</AppAlert>

    <AppButton type="submit" block :loading="isLoading" :disabled="!ready">Reset password and sign in</AppButton>

    <div class="rounded-lg bg-surface px-3 py-3 text-[13px] text-ink-muted">
      <p class="text-ink">Forgotten your password?</p>
      <p class="mt-1">
        Ask whoever gave you your account to reset it: Marien for an account's main user, or your
        account's main user for a sub account. You'll get a temporary password, and choose your own
        when you sign in.
      </p>
    </div>

    <router-link :to="{ name: 'login' }" class="text-center text-[13px] text-ink-muted hover:text-ink">
      Back to sign in
    </router-link>
  </form>
</template>
