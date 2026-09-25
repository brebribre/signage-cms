<script setup lang="ts">
/**
 * The hero's picture: the totem standing in a soft dome, the playlists that drive it beside
 * it, and a few cards floating round it that say the things a visitor asks first.
 *
 * It cycles on its own so the page shows what it does without being touched, and stops
 * cycling the moment someone picks a playlist themselves, because taking the wheel and then
 * being overridden is the rudest thing an auto-playing demo can do.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import IconBolt from '~icons/material-symbols/bolt'
import IconDevices from '~icons/material-symbols/devices-outline'

import PlaylistPicker from './PlaylistPicker.vue'
import SignageScreen from './SignageScreen.vue'
import { SLIDES } from '@/data/slides'

const CYCLE_MS = 3600
const active = ref(0)
let timer: number | undefined

function choose(i: number) {
  active.value = i
  // Hand control over for good.
  if (timer) { clearInterval(timer); timer = undefined }
}

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  timer = window.setInterval(() => { active.value = (active.value + 1) % SLIDES.length }, CYCLE_MS)
})
onBeforeUnmount(() => { if (timer) clearInterval(timer) })

const thumb = (i: number) => {
  const s = SLIDES[i]
  return s.src ? { backgroundImage: `url(${s.src})` } : { background: `linear-gradient(135deg, ${s.from}, ${s.to})` }
}
</script>

<template>
  <div class="relative mx-auto max-w-6xl">
    <!-- The dome and its rings, anchored to the floor the totem stands on. -->
    <div class="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center overflow-hidden" aria-hidden="true">
      <div class="relative h-[17rem] w-[34rem] sm:h-[21rem] sm:w-[42rem]">
        <div class="hero-ring absolute -inset-x-40 -top-40 bottom-0 rounded-t-full border-b-0" />
        <div class="hero-ring absolute -inset-x-20 -top-20 bottom-0 rounded-t-full border-b-0" />
        <div class="hero-dome absolute inset-0 rounded-t-full" />
      </div>
    </div>

    <div class="relative flex flex-col items-center gap-8 pt-6 sm:flex-row sm:items-end sm:justify-center sm:gap-6">
      <SignageScreen :active="active" />
      <!-- The playlists sit off the screen's shoulder, as the lettered answers do in a quiz. -->
      <div class="w-60 sm:mb-40 sm:-ml-10 sm:w-52">
        <PlaylistPicker :active="active" @select="choose" />
      </div>
    </div>

    <!-- The floating cards. Only where there is room for them; on a phone the page says the
         same things further down. -->
    <div class="pointer-events-none absolute inset-0 hidden lg:block">
      <div class="float pointer-events-auto absolute left-0 top-4 w-56 rounded-3xl bg-sky-strong p-6" style="--float-delay: -1s">
        <IconBolt class="size-8 text-brand-deep" aria-hidden="true" />
        <p class="display mt-5 text-4xl text-brand-deep">1 press</p>
        <p class="mt-1 text-sm text-brand-deep/80">To update every screen</p>
      </div>

      <div class="float pointer-events-auto absolute bottom-10 left-16 flex w-72 items-center gap-4 rounded-3xl bg-white p-3 shadow-[0_24px_60px_-28px_rgba(0,24,77,0.45)] ring-1 ring-line" style="--float-delay: -3s">
        <img src="/shots/screen-lobby.webp" alt="" class="h-24 w-20 shrink-0 rounded-2xl object-cover" decoding="async" />
        <div class="min-w-0">
          <p class="text-sm leading-snug text-ink">Pair a screen with a six letter code</p>
          <p class="mt-2.5 inline-block rounded-full bg-brand-deep px-3 py-1 font-mono text-xs tracking-[0.2em] text-white">K7P 2QX</p>
        </div>
      </div>

      <div class="float pointer-events-auto absolute right-0 top-0 w-52 rounded-3xl bg-white p-3 shadow-[0_24px_60px_-28px_rgba(0,24,77,0.45)] ring-1 ring-line" style="--float-delay: -2s">
        <div class="aspect-[4/3] rounded-2xl bg-page bg-cover bg-center transition-all duration-500" :style="thumb(active)" aria-hidden="true" />
        <p class="mt-3 flex items-center gap-1.5 px-1 text-[11px] uppercase tracking-wider text-ink-subtle">
          <span class="size-1.5 rounded-full bg-emerald-500" /> Now playing
        </p>
        <p class="px-1 pb-1 text-sm font-medium text-ink">{{ SLIDES[active].name }}</p>
      </div>

      <div class="float pointer-events-auto absolute bottom-16 right-8 w-48 rounded-3xl bg-brand-bright p-6 text-white" style="--float-delay: -4s">
        <IconDevices class="size-8" aria-hidden="true" />
        <p class="display mt-4 text-4xl">Any screen</p>
        <p class="mt-1 text-sm text-white/85">Android, smart TVs and browsers</p>
      </div>
    </div>
  </div>
</template>
