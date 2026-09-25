<script setup lang="ts">
/**
 * Settings → General: account-wide defaults, one compact row each. Staged like every other
 * setting that reaches screens — a Save appears once something has changed. The account defaults
 * are the owner's; your own password and Log out, at the bottom, are everyone's — on a phone
 * they have no other home.
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import IconLogout from '~icons/material-symbols/logout'
import IconCheck from '~icons/material-symbols/check'

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

    <!-- Everyone's: their own password, whatever their role. -->
    <div class="flex flex-col gap-3 rounded-2xl bg-canvas px-4 py-4">
      <p class="text-sm text-ink">Password</p>
      <div class="max-w-sm">
        <ChangePasswordContainer mode="settings" />
      </div>
    </div>

    <AppButton variant="secondary" size="sm" class="mt-3 self-start" :loading="loggingOut" @click="onLogout">
      <IconLogout v-if="!loggingOut" class="size-4" aria-hidden="true" />
      Log Out
    </AppButton>
  </div>
</template>
