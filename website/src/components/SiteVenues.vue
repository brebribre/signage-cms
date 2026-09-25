<script setup lang="ts">
/**
 * The strip under the hero, where a product page usually lists its customers. These are the
 * kinds of places Paskall is made for, set in a mix of type the way a logo wall is, so the
 * rhythm is there without claiming names we have no right to.
 */
import { computed } from 'vue'

import { useI18n } from '@/i18n'

const STYLES = [
  'font-serif italic text-2xl',
  'display font-semibold tracking-[0.18em] text-xl',
  'display text-2xl font-light',
  'font-serif text-2xl',
  'font-mono text-lg tracking-widest',
  'display text-2xl font-bold tracking-tight',
  'font-serif italic text-2xl font-semibold',
  'display text-lg font-medium tracking-[0.3em]',
]
const { m } = useI18n()
const VENUES = computed(() => m.value.venues.items.map((label, i) => ({ label, cls: STYLES[i] })))
</script>

<template>
  <section class="border-b border-line" :aria-label="m.venues.label">
    <div class="mx-auto max-w-7xl overflow-hidden px-5 py-10 sm:px-8">
      <!-- Faded at both ends so the loop slides in and out rather than being cut. -->
      <div class="[mask-image:linear-gradient(90deg,transparent,#000_12%,#000_88%,transparent)]">
        <ul class="marquee flex w-max items-center gap-16 text-ink/70">
          <li v-for="(v, i) in [...VENUES, ...VENUES]" :key="i" :class="v.cls" :aria-hidden="i >= VENUES.length">
            {{ v.label }}
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
