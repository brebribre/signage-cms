<script setup lang="ts">
/**
 * One screen as a card: its shape on the left, one fact per row on the right. Shared by the
 * Devices list (clicking opens the screen) and the deploy flow's picker (clicking selects it),
 * so a screen looks the same wherever you meet it. Presentational only — the caller handles
 * the click and says what's playing.
 */
import IconCheck from '~icons/material-symbols/check'
import IconLocation from '~icons/material-symbols/location-on-outline'
import IconLock from '~icons/material-symbols/lock-outline'
import IconPlayArrow from '~icons/material-symbols/play-arrow'
import IconSchedule from '~icons/material-symbols/schedule-outline'

import fortuLogoUrl from '@/assets/fortu-logo.png'
import { useFormat } from '@/hooks/useFormat'
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
}>(), { via: null, selectable: false, selected: false, disabled: false, note: null })

const { relativeTime } = useFormat()

// Every card reserves the same square footprint for its screen mock, so a portrait device never
// makes its card taller than the landscape ones around it — only what's drawn inside that
// footprint (see screenBox) changes with orientation, letterboxed to fit.
const SLOT_PX = 88

/** The rectangle drawn inside the fixed slot: the device's actual resolution when it has
 *  reported one, else a generic ratio for its orientation, scaled to fit within `SLOT_PX` on its
 *  longer side. Clamped at both ends so one very wide or very narrow screen can't collapse to
 *  nothing — this is a shape indicator, not a pixel-accurate preview. */
function screenBox(d: DeviceRead): { width: number; height: number } {
  const ratio = d.screen_width && d.screen_height
    ? d.screen_width / d.screen_height
    : d.orientation === 'portrait' ? 9 / 16 : 16 / 9
  const clamped = Math.min(Math.max(ratio, 0.4), 2.4)
  const width = clamped >= 1 ? SLOT_PX : Math.round(SLOT_PX * clamped)
  const height = clamped >= 1 ? Math.round(SLOT_PX / clamped) : SLOT_PX
  return { width: Math.max(width, 36), height: Math.max(height, 36) }
}
</script>

<template>
  <component
    :is="selectable ? 'button' : 'div'"
    :type="selectable ? 'button' : undefined"
    :disabled="selectable ? disabled : undefined"
    :aria-pressed="selectable ? selected : undefined"
    class="block w-full rounded-xl p-4 text-left transition-colors duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]"
    :class="[
      props.selected ? 'bg-raised ring-2 ring-ink ring-inset' : 'bg-surface',
      props.disabled ? 'cursor-not-allowed opacity-40' : 'cursor-pointer hover:bg-raised',
    ]"
  >
    <div class="flex items-center gap-4 sm:gap-6">
      <!-- A shape, not a pixel-accurate preview: the device's own aspect ratio and orientation,
           so a row of screens reads at a glance like the wall it maps to. -->
      <div
        class="flex shrink-0 items-center justify-center"
        :style="{ width: `${SLOT_PX}px`, height: `${SLOT_PX}px` }"
      >
        <div
          class="flex items-center justify-center overflow-hidden rounded-sm border-[5px] border-ink bg-canvas px-3 py-2"
          :style="{ width: `${screenBox(device).width}px`, height: `${screenBox(device).height}px` }"
        >
          <!-- The source file is a light wordmark on a transparent ground — invisible on this
               white screen mock — so it's used as a mask and painted solid black instead. -->
          <span
            class="block h-full w-full bg-ink"
            :style="{
              maskImage: `url(${fortuLogoUrl})`,
              WebkitMaskImage: `url(${fortuLogoUrl})`,
              maskRepeat: 'no-repeat',
              WebkitMaskRepeat: 'no-repeat',
              maskPosition: 'center',
              WebkitMaskPosition: 'center',
              maskSize: 'contain',
              WebkitMaskSize: 'contain',
            }"
            role="img"
            aria-label="Fortu logo"
          />
        </div>
      </div>

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
          <li v-if="note" class="flex items-center gap-2 py-1.5">
            <IconLock class="size-4 shrink-0 text-ink-subtle" aria-hidden="true" />
            <span class="min-w-0 truncate text-ink">{{ note }}</span>
          </li>
        </ul>
      </div>
    </div>
  </component>
</template>
