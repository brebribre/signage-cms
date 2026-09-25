<script setup lang="ts">
/** Where the player runs: three cards, one per kind of screen. */
import IconAndroid from '~icons/material-symbols/android'
import IconBrowser from '~icons/material-symbols/web'
import IconTv from '~icons/material-symbols/connected-tv-outline'

import { computed } from 'vue'

import { useI18n } from '@/i18n'

const LOOKS = [
  { icon: IconAndroid, tone: 'bg-tint', badge: 'bg-brand text-white' },
  { icon: IconTv, tone: 'bg-sky', badge: 'bg-brand-bright text-white' },
  { icon: IconBrowser, tone: 'bg-tint', badge: 'bg-brand-deep text-white' },
]
const { m } = useI18n()
const PLATFORMS = computed(() => LOOKS.map((l, i) => ({ ...l, ...m.value.platforms.items[i] })))
</script>

<template>
  <section id="platforms" class="mx-auto max-w-7xl px-5 pt-16 sm:px-8 sm:pt-20">
    <div class="reveal text-center">
      <span class="tag text-brand-deep">{{ m.platforms.tag }}</span>
      <h2 class="mt-5 text-4xl leading-[1.1] sm:text-5xl">{{ m.platforms.title }}</h2>
      <p class="mt-5 text-lg text-ink-muted">{{ m.platforms.subtitle }}</p>
    </div>
    <ul class="mt-12 grid gap-4 md:grid-cols-3">
      <li v-for="p in PLATFORMS" :key="p.badge" class="reveal flex flex-col rounded-3xl p-7" :class="p.tone">
        <span class="flex size-14 items-center justify-center rounded-2xl" :class="p.badge">
          <component :is="p.icon" class="size-8" aria-hidden="true" />
        </span>
        <h3 class="mt-6 text-2xl">{{ p.name }}</h3>
        <p class="mt-2 text-sm leading-relaxed text-ink-muted">{{ p.text }}</p>
      </li>
    </ul>
  </section>
</template>
