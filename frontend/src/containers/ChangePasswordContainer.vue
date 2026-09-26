<script setup lang="ts">
/**
 * Replacing your own password. Two uses:
 * - `first`: straight after signing in with a password someone else chose (staff issuing or
 *   resetting the account, or the main user making a sub account). Nothing else in the CMS
 *   works until this is done — the server refuses it — so whoever handed the password over
 *   never knows the one actually in use.
 * - `settings`: Settings → General, whenever someone wants a new one. There the form sits behind
 *   a Reset password button; on success it says `changed`, and the page closes it and says so.
 * The current password is always asked for. Every other session ends on success.
 */
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppInput from '@/reusables/AppInput.vue'

const props = defineProps<{ mode: 'first' | 'settings' }>()
const emit = defineEmits<{ changed: [] }>()

const router = useRouter()
const route = useRoute()
const { user, changePassword, logout, isLoading, error } = useAuth()

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
const ready = computed(() => current.value && next.value.length >= 8 && confirm.value === next.value && !problem.value)

async function onSubmit() {
  if (!ready.value) return
  if (!(await changePassword(current.value, next.value))) return
  if (props.mode === 'first') {
    router.push((route.query.next as string) || { name: 'now' })
    return
  }
  current.value = next.value = confirm.value = ''
  emit('changed')
}

async function onLogout() {
  await logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <form class="flex flex-col gap-4" @submit.prevent="onSubmit">
    <template v-if="mode === 'first'">
      <h1 class="text-2xl">Choose your own password</h1>
      <p class="text-[13px] text-ink-muted">
        Welcome{{ user ? `, ${user.display_name}` : '' }}. The password you signed in with was set
        for you. Choose one only you know — nobody else will see it.
      </p>
    </template>

    <AppInput
      id="current-password" v-model="current" type="password" required autocomplete="current-password"
      :label="mode === 'first' ? 'Password you were given' : 'Current password'"
    />
    <AppInput
      id="new-password" v-model="next" type="password" required autocomplete="new-password"
      label="New password" hint="At least 8 characters."
    />
    <AppInput
      id="confirm-password" v-model="confirm" type="password" required autocomplete="new-password"
      label="New password again"
    />

    <AppAlert v-if="problem" tone="danger">{{ problem }}</AppAlert>
    <AppAlert v-else-if="error" tone="danger">{{ error }}</AppAlert>

    <div class="flex flex-wrap items-center gap-3" :class="mode === 'first' && 'flex-col items-stretch'">
      <AppButton type="submit" :block="mode === 'first'" :size="mode === 'first' ? undefined : 'sm'"
                 :loading="isLoading" :disabled="!ready">
        {{ mode === 'first' ? 'Save and continue' : 'Change password' }}
      </AppButton>
      <button v-if="mode === 'first'" type="button" class="text-center text-[13px] text-ink-muted hover:text-ink" @click="onLogout">
        Log out instead
      </button>
    </div>
  </form>
</template>
