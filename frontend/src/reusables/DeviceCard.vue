<script setup lang="ts">
/**
 * One screen as a card: its shape on the left, one fact per row on the right. Shared by the
 * Devices list (clicking opens the screen) and the campaign screen picker (clicking selects it),
 * so a screen looks the same wherever you meet it. Presentational only — the caller handles
 * the click and says what's playing.
 */
import IconCheck from '~icons/material-symbols/check'
import IconLocation from '~icons/material-symbols/location-on-outline'
import IconLock from '~icons/material-symbols/lock-outline'
import IconPlayArrow from '~icons/material-symbols/play-arrow'
import IconSchedule from '~icons/material-symbols/schedule-outline'
import IconSystemUpdate from '~icons/material-symbols/system-update-alt'

import { useFormat } from '@/hooks/useFormat'
import ScreenShape from '@/reusables/ScreenShape.vue'
import StatusDot from '@/reusables/StatusDot.vue'
import type { DeviceRead } from '@/types/api'

const props = withDefaults(defineProps<{
  device: DeviceRead
  /** What the screen plays right now, and why — e.g. "Lobby loop" via "Breakfast". */
  playing: string
  via?: string | null
  /** Picker mode: a check beside the name, a ring when selected, rendered as a toggle button. */
  selectable?: boolean
  selected?: boolean
  disabled?: boolean
  /** Why a disabled card can't be picked, shown as its own row. */
  note?: string | null
  /** The app version this screen runs (and any update pending on it) — shown only where it
   *  matters, i.e. when picking screens for a software update. */
  versionLabel?: string | null
}>(), { via: null, selectable: false, selected: false, disabled: false, note: null, versionLabel: null })

const { relativeTime } = useFormat()
</script>

<template>
  <component
    :is="selectable ? 'button' : 'div'"
    :type="selectable ? 'button' : undefined"
    :disabled="selectable ? disabled : undefined"
    :aria-pressed="selectable ? selected : undefined"
    class="block w-full rounded-2xl p-4 text-left transition-colors duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]"
    :class="[
      props.selected ? 'bg-brand-soft ring-2 ring-brand ring-inset' : 'bg-canvas',
      props.disabled ? 'cursor-not-allowed opacity-40' : 'cursor-pointer hover:bg-surface',
    ]"
  >
    <div class="flex items-center gap-4 sm:gap-6">
      <ScreenShape :device="device" />

      <div class="min-w-0 flex-1">
        <div class="flex items-center gap-2">
          <p class="min-w-0 truncate text-base text-ink">{{ device.name || 'Unnamed screen' }}</p>
          <StatusDot :last-seen-at="device.last_seen_at" :show-label="false" class="shrink-0" />
          <span
            v-if="selectable"
            class="ml-auto flex size-5 shrink-0 items-center justify-center rounded-full border-2 transition-colors duration-150"
            :class="selected ? 'border-ink bg-ink text-ink-inverse' : 'border-line-strong'"
            aria-hidden="true"
          >
            <IconCheck v-if="selected" class="size-3.5" />
          </span>
        </div>
        <!-- One fact per row, each marked by an icon rather than a label. -->
        <ul class="mt-1.5 divide-y divide-line text-[13px] sm:max-w-md">
          <!-- Read-only: what a screen plays is decided in Campaigns, not here. -->
          <li class="flex items-center gap-2 py-1.5" title="Playing">
            <IconPlayArrow class="size-4 shrink-0 text-ink-subtle" aria-label="Playing" />
            <span class="min-w-0 truncate text-ink">
              {{ playing }}<span v-if="via" class="text-ink-subtle"> {{ via }}</span>
            </span>
          </li>
          <li v-if="device.location" class="flex items-center gap-2 py-1.5" title="Location">
            <IconLocation class="size-4 shrink-0 text-ink-subtle" aria-label="Location" />
            <span class="min-w-0 truncate text-ink">{{ device.location }}</span>
          </li>
          <li class="flex items-center gap-2 py-1.5" title="Last seen">
            <IconSchedule class="size-4 shrink-0 text-ink-subtle" aria-label="Last seen" />
            <span class="text-ink">{{ relativeTime(device.last_seen_at) }}</span>
          </li>
          <li v-if="versionLabel" class="flex items-center gap-2 py-1.5" title="App version">
            <IconSystemUpdate class="size-4 shrink-0 text-ink-subtle" aria-label="App version" />
            <span class="min-w-0 truncate text-ink tabular-nums">{{ versionLabel }}</span>
          </li>
          <li v-if="note" class="flex items-center gap-2 py-1.5">
            <IconLock class="size-4 shrink-0 text-ink-subtle" aria-hidden="true" />
            <span class="min-w-0 truncate text-ink">{{ note }}</span>
          </li>
        </ul>
      </div>
    </div>
  </component>
</template>
