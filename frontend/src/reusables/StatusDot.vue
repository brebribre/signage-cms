<script setup lang="ts">
import { computed } from 'vue'

/**
 * A screen's liveness, from when it last heartbeat. Thresholds match the device's own
 * poll cadence (Phase 10, 30s) with headroom for one or two missed beats before amber,
 * and enough more before grey that a screen rebooting doesn't flicker red.
 */
const props = defineProps<{ lastSeenAt: string | null }>()

const state = computed<'live' | 'stale' | 'offline'>(() => {
  if (!props.lastSeenAt) return 'offline'
  const mins = (Date.now() - new Date(props.lastSeenAt).getTime()) / 60_000
  if (mins < 2) return 'live'
  if (mins < 15) return 'stale'
  return 'offline'
})

// No accent hue in this palette, so liveness is the one place a state genuinely needs a
// colour outside ink/gray to be scannable in a list — a dot, not a fill, keeps it a status
// indicator rather than a competing splash of colour.
const CLASSES = {
  live: 'bg-emerald-600',
  stale: 'bg-amber-500',
  offline: 'bg-ink-subtle',
} as const

const LABEL = { live: 'Online', stale: 'Slow to respond', offline: 'Offline' } as const
</script>

<template>
  <span class="inline-flex items-center gap-1.5" :title="LABEL[state]">
    <span class="size-2 shrink-0 rounded-full" :class="CLASSES[state]" aria-hidden="true" />
    <span class="text-[13px] text-ink-muted">{{ LABEL[state] }}</span>
  </span>
</template>
