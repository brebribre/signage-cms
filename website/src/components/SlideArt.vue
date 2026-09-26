<script setup lang="ts">
/**
 * One demo slide, drawn in the site's own look rather than a stock photo: a white, sky or
 * periwinkle ground, always light, the diagonal wave of the brand blues across its top right, an icon tile, and the
 * words set large at the foot.
 *
 * It measures itself in container units of its shorter side (cqmin), so the same slide lays
 * out properly on a landscape screen, a portrait totem, or a thumbnail, which passes `thumb`
 * to leave the words off.
 */
import { computed } from 'vue'
import IconWork from '~icons/material-symbols/work-outline'
import IconDish from '~icons/material-symbols/restaurant'
import IconClock from '~icons/material-symbols/schedule-outline'
import IconWave from '~icons/material-symbols/waving-hand-outline'

import type { Slide } from '@/data/slides'

const props = defineProps<{ slide: Slide; thumb?: boolean }>()

const ICONS = { clock: IconClock, dish: IconDish, work: IconWork, wave: IconWave }
const LOOK = {
  light: { ground: 'bg-white', wave: 'slide-wave', badge: 'bg-brand-deep text-white', title: 'text-ink', sub: 'text-ink-muted' },
  sky: { ground: 'bg-sky', wave: 'slide-wave', badge: 'bg-brand-bright text-white', title: 'text-brand-deep', sub: 'text-brand-deep/70' },
  tint: { ground: 'bg-tint', wave: 'slide-wave', badge: 'bg-brand text-white', title: 'text-brand-deep', sub: 'text-brand-deep/70' },
}
const look = computed(() => LOOK[props.slide.tone])
</script>

<template>
  <div class="relative size-full overflow-hidden [container-type:size]" :class="look.ground">
    <div class="absolute inset-0" :class="look.wave" aria-hidden="true" />
    <span
      class="absolute left-[9cqmin] top-[9cqmin] flex items-center justify-center"
      :class="[look.badge, thumb ? 'size-[34cqmin] rounded-[9cqmin]' : 'size-[17cqmin] rounded-[5cqmin]']"
      aria-hidden="true"
    >
      <component :is="ICONS[slide.icon]" :class="thumb ? 'size-[20cqmin]' : 'size-[10cqmin]'" />
    </span>
    <div v-if="!thumb" class="absolute inset-x-[9cqmin] bottom-[9cqmin]">
      <p class="display text-[13cqmin] leading-[1.02]" :class="look.title">{{ slide.title }}</p>
      <p class="mt-[3cqmin] text-[7.5cqmin] leading-snug" :class="look.sub">{{ slide.sub }}</p>
    </div>
  </div>
</template>
