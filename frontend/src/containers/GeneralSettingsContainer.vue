<script setup lang="ts">
/**
 * Settings → General: account-wide defaults. Staged like every other setting that reaches
 * screens — nothing changes until Save.
 */
import { computed, ref, watch } from 'vue'
import IconCheck from '~icons/material-symbols/check'

import { useAccountSettings } from '@/hooks/useAccountSettings'
import { useAuth } from '@/hooks/useAuth'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import { browserZone, zoneOptions } from '@/utils/timezones'

const { account } = useAuth()
const { isSaving, error, save } = useAccountSettings()

const saved = computed(() => account.value?.default_timezone ?? 'UTC')
const timezone = ref(saved.value)
watch(saved, (value) => { timezone.value = value })

const here = browserZone()
const options = computed(() => zoneOptions(saved.value, here))
const isDirty = computed(() => timezone.value !== saved.value)

const justSaved = ref(false)
async function onSave() {
  if (await save({ default_timezone: timezone.value })) {
    justSaved.value = true
    setTimeout(() => { justSaved.value = false }, 2500)
  }
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>

    <AppCard class="flex flex-col gap-4 sm:p-5">
      <div class="flex flex-col gap-1.5 sm:max-w-sm">
        <label for="default-timezone" class="text-sm text-ink">Default timezone</label>
        <select
          id="default-timezone"
          v-model="timezone"
          aria-describedby="default-timezone-help"
          class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm text-ink
                 focus:border-brand focus:outline-none"
        >
          <option v-for="z in options" :key="z" :value="z">
            {{ z }}{{ z === here ? ' (this browser)' : '' }}
          </option>
        </select>
        <p id="default-timezone-help" class="text-[13px] text-ink-muted">
          Screens you pair from now on start in this timezone, which their schedules and power
          times are read in. Screens already paired keep their own — change those on each screen's page.
        </p>
      </div>

      <div class="flex items-center gap-3">
        <AppButton size="sm" :disabled="!isDirty" :loading="isSaving" @click="onSave">Save changes</AppButton>
        <span v-if="justSaved" class="inline-flex items-center gap-1 text-[13px] text-ink-muted" role="status">
          <IconCheck class="size-4 text-brand" aria-hidden="true" />
          Saved
        </span>
      </div>
    </AppCard>
  </div>
</template>
