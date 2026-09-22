<script setup lang="ts">
import { computed } from 'vue'

import { useAccountLimits } from '@/hooks/useAccountLimits'
import { useFormat } from '@/hooks/useFormat'
import AppAlert from '@/reusables/AppAlert.vue'
import AppCard from '@/reusables/AppCard.vue'
import ProgressBar from '@/reusables/ProgressBar.vue'

/**
 * Settings → Plan & limits: how many screens and how much storage the account may use, and how
 * much of each is used. Read-only on purpose — the numbers are set by Paskall when the account
 * is issued, and changing them is a conversation, not a button.
 */
const { limits, isLoading, error, screensFraction, storageFraction } = useAccountLimits()
const { bytes } = useFormat()

/** Near the limit deserves a warning colour; at it, red. */
function tone(fraction: number | null): string {
  if (fraction === null) return 'text-ink'
  if (fraction >= 1) return 'text-danger'
  if (fraction >= 0.9) return 'text-amber-600'
  return 'text-ink'
}

const rows = computed(() => {
  const l = limits.value
  if (!l) return []
  return [
    {
      key: 'screens',
      label: 'Screens',
      used: `${l.screens_used} screen${l.screens_used === 1 ? '' : 's'}`,
      limit: l.max_screens === null ? 'No limit set' : `of ${l.max_screens}`,
      fraction: screensFraction.value,
      note: l.max_screens === null
        ? 'Connect as many screens as you need.'
        : l.screens_used >= l.max_screens
          ? 'Every seat is taken. Remove a screen to connect another, or ask for a higher limit.'
          : `${l.max_screens - l.screens_used} more can be connected.`,
    },
    {
      key: 'storage',
      label: 'Storage',
      used: bytes(l.storage_used_bytes),
      limit: l.storage_quota_bytes === null ? 'No quota set' : `of ${bytes(l.storage_quota_bytes)}`,
      fraction: storageFraction.value,
      note: `${l.file_count} file${l.file_count === 1 ? '' : 's'} in the media library.`
        + (l.storage_quota_bytes !== null && l.storage_used_bytes >= l.storage_quota_bytes
          ? ' The quota is full: delete files you no longer use, or ask for more space.'
          : ''),
    },
  ]
})
</script>

<template>
  <div class="flex flex-col gap-4">
    <p class="text-sm text-ink-muted">
      What this account may use. To change a limit, contact Paskall.
    </p>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <p v-else-if="isLoading && !limits" class="text-sm text-ink-muted">Loading…</p>

    <AppCard v-for="row in rows" :key="row.key" class="flex flex-col gap-3">
      <div class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <p class="text-sm text-ink">{{ row.label }}</p>
        <p class="text-sm tabular-nums">
          <b :class="tone(row.fraction)">{{ row.used }}</b>{{ ' ' }}<span class="text-ink-muted">{{ row.limit }}</span>
        </p>
      </div>
      <ProgressBar v-if="row.fraction !== null" :value="row.fraction" />
      <p class="text-[13px] text-ink-muted">{{ row.note }}</p>
    </AppCard>
  </div>
</template>
