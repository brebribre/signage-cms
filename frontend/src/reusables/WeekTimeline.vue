<script setup lang="ts">
/** A week at a glance: one 24h bar per day, each slot drawn where it plays, and everything
 *  uncovered left grey — the screen asleep. Presentational only; it is handed windows and
 *  labels, not playlists. Square corners throughout, so the bars read as a grid of time rather
 *  than a stack of pills. */
import IconBedtime from '~icons/material-symbols/bedtime-outline'

import { DAY_BITS } from '@/types/api'
import { DAY_MINUTES, segmentsOnDay } from '@/utils/scheduleMath'
import type { TimelineSlot } from '@/utils/scheduleMath'

const props = defineProps<{ slots: TimelineSlot[] }>()

// What plays is the active thing on this page, so it carries the brand blues (the tokens in
// style.css: brand, brand-bright, brand-hover, then a lighter tint of brand), all readable
// against the light grey "asleep" ground the bars sit on.
const TONES = ['#003399', '#0076dd', '#1f55c4', '#7fa1e6'] as const
const toneOf = (i: number) => TONES[i % TONES.length]

const pct = (minutes: number) => `${(minutes / DAY_MINUTES) * 100}%`

function blocks(day: number) {
  return props.slots.flatMap((s) =>
    segmentsOnDay(s, day).map(([start, end], i) => ({ key: `${s.key}-${i}`, slot: s, start, end })),
  )
}

/** One legend entry per tone actually in use — a playlist used by three slots is one swatch. */
function legend() {
  const seen = new Map<number, string>()
  for (const s of props.slots) if (!seen.has(s.tone)) seen.set(s.tone, s.label)
  return [...seen.entries()]
}
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <div class="ml-10 flex justify-between text-[11px] text-ink-subtle">
      <span>00</span><span>06</span><span>12</span><span>18</span><span>24</span>
    </div>
    <div v-for="(d, day) in DAY_BITS" :key="d.bit" class="flex items-center gap-2">
      <span class="w-8 shrink-0 text-[12px] text-ink-muted">{{ d.short }}</span>
      <div class="relative h-6 flex-1 overflow-hidden bg-line">
        <div
          v-for="b in blocks(day)"
          :key="b.key"
          class="absolute inset-y-0"
          :class="b.slot.invalid && 'ring-2 ring-danger ring-inset'"
          :style="{ left: pct(b.start), width: pct(b.end - b.start), background: toneOf(b.slot.tone) }"
          :title="`${b.slot.label} · ${b.slot.starts_at}–${b.slot.ends_at}`"
        />
      </div>
    </div>
    <div class="mt-2 ml-10 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[12px] text-ink-muted">
      <span v-for="[tone, label] in legend()" :key="tone" class="flex items-center gap-1.5">
        <span class="size-3" :style="{ background: toneOf(tone) }" />
        {{ label }}
      </span>
      <span class="flex items-center gap-1.5">
        <span class="flex size-3 items-center justify-center bg-line">
          <IconBedtime class="size-2.5 text-ink-muted" />
        </span>
        Asleep
      </span>
    </div>
  </div>
</template>
