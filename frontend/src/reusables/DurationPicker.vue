<script setup lang="ts">
/**
 * How long a scene without a natural length (image, website, custom) stays on screen —
 * anywhere from a few seconds to multiple days, so a plain "seconds" box stops being the
 * only way in. The button shows the current value compactly; the popover breaks it into
 * days/hours/minutes/seconds so a long dwell time doesn't mean typing "86400".
 */
import { onMounted, onUnmounted, ref } from 'vue'
import IconScheduleOutline from '~icons/material-symbols/schedule-outline'

const model = defineModel<number>({ default: 10 })

const DAY = 86400
const HOUR = 3600
const MINUTE = 60

function partsFrom(totalSeconds: number) {
  let remaining = Math.max(0, Math.round(totalSeconds))
  const days = Math.floor(remaining / DAY)
  remaining -= days * DAY
  const hours = Math.floor(remaining / HOUR)
  remaining -= hours * HOUR
  const minutes = Math.floor(remaining / MINUTE)
  remaining -= minutes * MINUTE
  return { days, hours, minutes, seconds: remaining }
}

function labelFor(totalSeconds: number): string {
  const { days, hours, minutes, seconds } = partsFrom(totalSeconds)
  if (days) return hours ? `${days}d ${hours}h` : `${days}d`
  if (hours) return minutes ? `${hours}h ${minutes}m` : `${hours}h`
  if (minutes) return seconds ? `${minutes}m ${seconds}s` : `${minutes}m`
  return `${seconds}s`
}

/** One field at a time, everything else held as-is — typing "2" into hours shouldn't
 *  reset days or seconds back to what they were before the popover opened. */
function setPart(key: 'days' | 'hours' | 'minutes' | 'seconds', raw: number) {
  const parts = partsFrom(model.value)
  parts[key] = Number.isFinite(raw) ? Math.max(0, Math.round(raw)) : 0
  model.value = Math.max(1, parts.days * DAY + parts.hours * HOUR + parts.minutes * MINUTE + parts.seconds)
}

const open = ref(false)
const root = ref<HTMLElement | null>(null)

function close() {
  open.value = false
}
function onDocClick(e: MouseEvent) {
  if (open.value && root.value && !root.value.contains(e.target as Node)) close()
}
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') close()
}
onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div ref="root" class="relative inline-block" @click.stop>
    <button
      type="button"
      class="flex items-center gap-1 rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px]
             text-ink transition-colors duration-150 hover:border-ink"
      aria-haspopup="dialog"
      :aria-expanded="open"
      @click="open = !open"
    >
      <IconScheduleOutline class="size-3.5 text-ink-muted" />
      {{ labelFor(model) }}
    </button>

    <div
      v-if="open"
      role="dialog"
      aria-label="Set duration"
      class="absolute right-0 z-20 mt-1 w-56 rounded-xl border border-line bg-canvas p-3"
    >
      <p class="mb-2 text-[12px] text-ink-subtle">How long this stays on screen</p>
      <div class="grid grid-cols-4 gap-1.5">
        <label class="flex flex-col items-center gap-1">
          <input
            type="number" min="0" :value="partsFrom(model).days"
            class="w-full rounded-md border border-line-strong bg-surface px-1 py-1 text-center text-[13px]
                   text-ink focus:border-ink focus:outline-none"
            @input="setPart('days', ($event.target as HTMLInputElement).valueAsNumber)"
          />
          <span class="text-[11px] text-ink-subtle">days</span>
        </label>
        <label class="flex flex-col items-center gap-1">
          <input
            type="number" min="0" max="23" :value="partsFrom(model).hours"
            class="w-full rounded-md border border-line-strong bg-surface px-1 py-1 text-center text-[13px]
                   text-ink focus:border-ink focus:outline-none"
            @input="setPart('hours', ($event.target as HTMLInputElement).valueAsNumber)"
          />
          <span class="text-[11px] text-ink-subtle">hrs</span>
        </label>
        <label class="flex flex-col items-center gap-1">
          <input
            type="number" min="0" max="59" :value="partsFrom(model).minutes"
            class="w-full rounded-md border border-line-strong bg-surface px-1 py-1 text-center text-[13px]
                   text-ink focus:border-ink focus:outline-none"
            @input="setPart('minutes', ($event.target as HTMLInputElement).valueAsNumber)"
          />
          <span class="text-[11px] text-ink-subtle">min</span>
        </label>
        <label class="flex flex-col items-center gap-1">
          <input
            type="number" min="0" max="59" :value="partsFrom(model).seconds"
            class="w-full rounded-md border border-line-strong bg-surface px-1 py-1 text-center text-[13px]
                   text-ink focus:border-ink focus:outline-none"
            @input="setPart('seconds', ($event.target as HTMLInputElement).valueAsNumber)"
          />
          <span class="text-[11px] text-ink-subtle">sec</span>
        </label>
      </div>
    </div>
  </div>
</template>
