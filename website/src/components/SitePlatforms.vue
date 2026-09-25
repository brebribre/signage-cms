<script setup lang="ts">
/** Where the player runs: three cards, one per kind of screen. */
import IconAndroid from '~icons/material-symbols/android'
import IconBrowser from '~icons/material-symbols/web'
import IconTv from '~icons/material-symbols/connected-tv-outline'

const PLATFORMS = [
  {
    icon: IconAndroid, name: 'Android', tone: 'bg-tint', badge: 'bg-brand text-white',
    text: 'The Paskall player app on Android TV boxes and tablets. Plays 4K video, and can be fully managed from afar.',
    chips: ['Android TV boxes', 'Tablets', '4K'],
  },
  {
    icon: IconTv, name: 'Smart TV browser', tone: 'bg-sky', badge: 'bg-brand-bright text-white',
    text: 'Open the player in the TV’s own browser. No box to buy, nothing to install.',
    chips: ['Samsung Tizen', 'LG webOS', '1080p'],
  },
  {
    icon: IconBrowser, name: 'Browser', tone: 'bg-tint', badge: 'bg-brand-deep text-white',
    text: 'A Chromebox, a mini PC or any computer running the player in a browser, full screen, becomes a screen in your fleet.',
    chips: ['Chromebox', 'Mini PC', 'Kiosk mode'],
  },
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
      <li v-for="p in PLATFORMS" :key="p.name" class="reveal flex flex-col rounded-3xl p-7" :class="p.tone">
        <span class="flex size-14 items-center justify-center rounded-2xl" :class="p.badge">
          <component :is="p.icon" class="size-8" aria-hidden="true" />
        </span>
        <h3 class="mt-6 text-2xl">{{ p.name }}</h3>
        <p class="mt-2 text-sm leading-relaxed text-ink-muted">{{ p.text }}</p>
        <ul class="mt-auto flex flex-wrap gap-2 pt-6">
          <li v-for="c in p.chips" :key="c" class="rounded-full bg-white px-3 py-1 text-xs text-ink ring-1 ring-line">{{ c }}</li>
        </ul>
      </li>
    </ul>
  </section>
</template>
