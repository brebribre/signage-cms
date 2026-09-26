<script setup lang="ts">
/**
 * Settings → General: account-wide defaults, one compact row each. Staged like every other
 * setting that reaches screens — a Save appears once something has changed. The account defaults
 * are the owner's; your own password and Log out, at the bottom, are everyone's — on a phone
 * they have no other home.
 */
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import IconLogout from '~icons/material-symbols/logout'
import IconCheck from '~icons/material-symbols/check'
import IconKey from '~icons/material-symbols/key-outline'

import { useAccountSettings } from '@/hooks/useAccountSettings'
import { useAuth } from '@/hooks/useAuth'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppSelect from '@/reusables/AppSelect.vue'
import ChangePasswordContainer from '@/containers/ChangePasswordContainer.vue'
import { browserZone, zoneOptions } from '@/utils/timezones'

const router = useRouter()
const { account, isOwner, logout } = useAuth()
const { isSaving, error, save } = useAccountSettings()

const saved = computed(() => account.value?.default_timezone ?? 'UTC')
const timezone = ref(saved.value)
watch(saved, (value) => { timezone.value = value })

const here = browserZone()
const options = computed(() =>
  zoneOptions(saved.value, here).map((z) => ({ value: z, label: z, hint: z === here ? 'this browser' : undefined })),
)
const isDirty = computed(() => timezone.value !== saved.value)

const justSaved = ref(false)
async function onSave() {
  if (await save({ default_timezone: timezone.value })) {
    justSaved.value = true
    setTimeout(() => { justSaved.value = false }, 2000)
  }
}

const loggingOut = ref(false)
async function onLogout() {
  loggingOut.value = true
  try {
    await logout()
  } finally {
    router.push({ name: 'login' })
  }
}

// --- Your own password: a button that opens the form, which closes itself once it's done ---

const changingPassword = ref(false)
const passwordChanged = ref(false)
let changedTimer: ReturnType<typeof setTimeout> | undefined

async function togglePassword() {
  changingPassword.value = !changingPassword.value
  passwordChanged.value = false
  if (changingPassword.value) {
    // Straight into the first field: opening the form is asking to type in it.
    await nextTick()
    document.getElementById('current-password')?.focus()
  }
}

function onPasswordChanged() {
  changingPassword.value = false
  passwordChanged.value = true
  clearTimeout(changedTimer)
  changedTimer = setTimeout(() => (passwordChanged.value = false), 6000)
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>

    <div v-if="isOwner" class="flex flex-col gap-2 rounded-2xl bg-canvas px-4 py-3 sm:flex-row sm:items-center sm:gap-4">
      <!-- The setting's name says what it is for; new screens start in this zone. -->
      <label for="default-timezone" class="text-sm text-ink sm:w-40 sm:shrink-0">Default timezone</label>
      <AppSelect id="default-timezone" v-model="timezone" :options="options" size="sm" class="sm:w-64" />
      <div v-if="isDirty || justSaved" class="flex items-center sm:ml-auto">
        <AppButton v-if="isDirty" size="sm" :loading="isSaving" @click="onSave">Save</AppButton>
        <span v-else-if="justSaved" class="inline-flex items-center gap-1 text-[13px] text-ink-muted" role="status">
          <IconCheck class="size-4 text-brand" aria-hidden="true" />
          Saved
        </span>
      </div>
    </div>

    <!-- Everyone's: their own password, whatever their role. Closed until asked for — a form
         that is always open reads as something to fill in. -->
    <div class="rounded-2xl bg-canvas px-4 py-4">
      <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
        <p class="text-sm text-ink sm:w-40 sm:shrink-0">Password</p>
        <AppButton
          :variant="changingPassword ? 'ghost' : 'secondary'"
          size="sm"
          :aria-expanded="changingPassword"
          aria-controls="password-form"
          @click="togglePassword"
        >
          <IconKey v-if="!changingPassword" class="size-4" aria-hidden="true" />
          {{ changingPassword ? 'Cancel' : 'Reset password' }}
        </AppButton>
        <span v-if="passwordChanged" class="inline-flex items-center gap-1 text-[13px] text-ink-muted" role="status">
          <IconCheck class="size-4 text-brand" aria-hidden="true" />
          Password changed. Other devices are signed out.
        </span>
      </div>
      <Transition
        enter-active-class="transition duration-200 ease-out motion-reduce:transition-none"
        enter-from-class="opacity-0 -translate-y-1"
        leave-active-class="transition duration-150 ease-in motion-reduce:transition-none"
        leave-to-class="opacity-0 -translate-y-1"
      >
        <div v-if="changingPassword" id="password-form" class="mt-4 max-w-sm border-t border-line pt-4">
          <ChangePasswordContainer mode="settings" @changed="onPasswordChanged" />
        </div>
      </Transition>
    </div>

    <AppButton variant="secondary" size="sm" class="mt-3 self-start" :loading="loggingOut" @click="onLogout">
      <IconLogout v-if="!loggingOut" class="size-4" aria-hidden="true" />
      Log Out
    </AppButton>
  </div>
</template>
