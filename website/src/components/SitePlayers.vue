<script setup lang="ts">
import IconAndroid from '~icons/material-symbols/android'
import IconLanguage from '~icons/material-symbols/language'
import IconTv from '~icons/material-symbols/tv-outline'

const PLAYERS = [
  { icon: IconAndroid, title: 'Android player', text: 'For Android TV boxes and tablets. Plays up to 4K, updates itself over the air, and on a managed box switches the display off on schedule and keeps other apps out.' },
  { icon: IconTv, title: 'Smart TV browser', text: 'Samsung, LG or any TV with a browser: open one address, press OK once, and the TV is a screen. Media is stored in the browser and plays through the TV’s own decoder.' },
  { icon: IconLanguage, title: 'Any browser', text: 'A laptop behind a window, a Raspberry Pi, a kiosk. If it opens a web page it can be a Paskall screen, portrait or landscape, with the same pairing code.' },
]
</script>

<template>
  <section id="players" class="relative overflow-hidden bg-brand-deep text-ink-inverse">
    <div class="absolute inset-0 brand-gradient opacity-90" aria-hidden="true" />
    <div class="relative mx-auto max-w-6xl px-5 py-20 sm:px-8 sm:py-28">
      <div class="grid items-center gap-12 lg:grid-cols-2">
        <div class="reveal">
          <p class="text-[13px] uppercase tracking-wider text-white/70">Players</p>
          <h2 class="mt-3 text-3xl sm:text-4xl">One code. Any screen.</h2>
          <p class="mt-4 leading-relaxed text-white/80">
            Every player shows the same pairing screen and speaks the same language to the CMS, so a fleet can mix hardware without anyone noticing.
          </p>
          <ul class="mt-8 flex flex-col gap-5">
            <li v-for="p in PLAYERS" :key="p.title" class="flex gap-4">
              <span class="inline-flex size-10 shrink-0 items-center justify-center rounded-xl bg-white/10">
                <component :is="p.icon" class="size-5" />
              </span>
              <div>
                <h3 class="text-base">{{ p.title }}</h3>
                <p class="mt-1 text-sm leading-relaxed text-white/75">{{ p.text }}</p>
              </div>
            </li>
          </ul>
        </div>
        <figure class="reveal overflow-hidden rounded-2xl border border-white/15 shadow-[0_40px_100px_-30px_rgba(0,0,0,0.6)]">
          <img src="/shots/player-pairing.webp" alt="The Paskall player's pairing screen: a six-letter code on the brand gradient" class="block w-full" loading="lazy" decoding="async" />
        </figure>
      </div>
    </div>
  </section>
</template>
