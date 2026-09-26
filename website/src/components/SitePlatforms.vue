<script setup lang="ts">
/** Where the player runs, as one of the feature cards: a tile for each kind of screen. */
import { computed } from 'vue'
import IconAndroid from '~icons/material-symbols/android'
import IconBrowser from '~icons/material-symbols/web'
import IconTv from '~icons/material-symbols/connected-tv-outline'

import FeatureCard from './FeatureCard.vue'
import { useI18n } from '@/i18n'

const LOOKS = [
  { icon: IconAndroid, badge: 'bg-brand text-white' },
  { icon: IconTv, badge: 'bg-brand-bright text-white' },
  { icon: IconBrowser, badge: 'bg-brand-deep text-white' },
]
const { m } = useI18n()
const PLATFORMS = computed(() => LOOKS.map((l, i) => ({ ...l, ...m.value.platforms.items[i] })))
</script>

<template>
  <section id="platforms">
    <FeatureCard pattern="twin">
      <h3 class="text-3xl leading-[1.1] sm:text-4xl">{{ m.platforms.lead }}</h3>
      <p class="mt-3 max-w-md leading-relaxed text-ink-muted">{{ m.platforms.rest }}</p>

      <template #visual>
        <!-- Three tiles on the sweep; side by side when the card is wide enough. -->
        <ul class="grid gap-2.5 pr-6 pb-6 pt-2 sm:gap-3 sm:pr-8 sm:pb-8 lg:pr-10 lg:pb-10 @xl:grid-cols-3">
          <li
            v-for="p in PLATFORMS" :key="p.badge"
            class="flex items-start gap-3 rounded-xl bg-white/90 p-4 shadow-[0_20px_50px_-30px_rgba(0,24,77,0.5)] ring-1 ring-white backdrop-blur @xl:flex-col @xl:gap-4 @xl:p-5"
          >
            <span class="flex size-10 shrink-0 items-center justify-center rounded-lg @xl:size-12 @xl:rounded-lg" :class="p.badge">
              <component :is="p.icon" class="size-6 @xl:size-7" aria-hidden="true" />
            </span>
            <span>
              <span class="display block text-lg text-ink @xl:text-xl">{{ p.name }}</span>
              <span class="mt-1 block text-sm leading-relaxed text-ink-muted">{{ p.text }}</span>
            </span>
          </li>
        </ul>
      </template>
    </FeatureCard>
  </section>
</template>
