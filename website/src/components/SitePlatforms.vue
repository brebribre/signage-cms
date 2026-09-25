<script setup lang="ts">
/** Where the player runs: three cards, one per kind of screen. */
import IconAndroid from '~icons/material-symbols/android'
import IconBrowser from '~icons/material-symbols/web'
import IconTv from '~icons/material-symbols/connected-tv-outline'

const PLATFORMS = [
  { icon: IconAndroid, name: 'Android', tone: 'bg-tint', badge: 'bg-brand text-white' },
  { icon: IconTv, name: 'Smart TV browser', tone: 'bg-sky', badge: 'bg-brand-bright text-white' },
  { icon: IconBrowser, name: 'Browser', tone: 'bg-tint', badge: 'bg-brand-deep text-white' },
]
</script>

<template>
  <section id="platforms" class="mx-auto max-w-7xl px-5 pt-16 sm:px-8 sm:pt-20">
    <div class="reveal text-center">
      <span class="tag text-brand-deep">Platforms</span>
      <h2 class="mt-5 text-4xl leading-[1.1] sm:text-5xl">Designed for versatility</h2>
      <p class="mt-5 text-lg text-ink-muted">One player, on whatever screen you already have.</p>
    </div>
    <ul class="mt-12 grid gap-4 md:grid-cols-3">
      <li v-for="p in PLATFORMS" :key="p.name" class="reveal flex items-center gap-5 rounded-3xl p-7 sm:p-8" :class="p.tone">
        <span class="flex size-16 shrink-0 items-center justify-center rounded-2xl" :class="p.badge">
          <component :is="p.icon" class="size-9" aria-hidden="true" />
        </span>
        <h3 class="text-3xl leading-tight lg:text-4xl">{{ p.name }}</h3>
      </li>
    </ul>
  </section>
</template>
