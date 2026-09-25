<script setup lang="ts">
/** Where the player runs: three cards, one per kind of screen. */
import IconAndroid from '~icons/material-symbols/android'
import IconBrowser from '~icons/material-symbols/web'
import IconTv from '~icons/material-symbols/connected-tv-outline'

const PLATFORMS = [
  { icon: IconAndroid, name: 'Android', tone: 'bg-tint', badge: 'bg-brand text-white',
    text: 'Install our .apk on Android TV boxes and devices.' },
  { icon: IconTv, name: 'Smart TV browser', tone: 'bg-sky', badge: 'bg-brand-bright text-white',
    text: 'Utilizes the smart TV’s browser and requires no installation.' },
  { icon: IconBrowser, name: 'Browser', tone: 'bg-tint', badge: 'bg-brand-deep text-white',
    text: 'Any device that runs a browser.' },
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
      </li>
    </ul>
  </section>
</template>
