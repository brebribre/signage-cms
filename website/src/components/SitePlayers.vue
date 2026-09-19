<script setup lang="ts">
import IconAndroid from '~icons/material-symbols/android'
import IconLanguage from '~icons/material-symbols/language'
import IconTv from '~icons/material-symbols/tv-outline'

import DeviceFrame from './DeviceFrame.vue'

const PLAYERS = [
  { icon: IconAndroid, title: 'Android player', text: 'For Android TV boxes and tablets. Plays up to 4K, updates itself over the air, and on a managed box switches the display off on schedule and keeps every other app out.' },
  { icon: IconTv, title: 'Smart TV browser', text: 'Samsung, LG, or any TV with a browser: open one address, press OK once, and the TV is a screen. Media is stored in the browser and plays through the TV’s own decoder.' },
  { icon: IconLanguage, title: 'Any browser', text: 'A laptop behind a window, a Raspberry Pi, a kiosk. If it opens a web page it can be a Paskall screen, portrait or landscape, with the same six-letter code.' },
]
</script>

<template>
  <!-- The dark stretch, entered on a diagonal — the change of pace Stripe uses to separate
       "what it is" from "what it runs on". -->
  <section id="players" class="angled-band angled-band-up relative -mt-[7vw] text-ink-inverse">
    <div class="relative mx-auto max-w-7xl px-5 pt-[calc(7vw+5rem)] pb-24 sm:px-8 sm:pb-28">
      <div class="grid items-center gap-12 lg:grid-cols-12 lg:gap-14">
        <div class="reveal lg:col-span-5">
          <p class="text-[13px] font-medium uppercase tracking-wider text-white/70">Players</p>
          <h2 class="mt-3 text-3xl leading-tight sm:text-4xl">One code. Any screen.</h2>
          <p class="mt-4 leading-relaxed text-white/80">
            Every player shows the same pairing screen and speaks the same language to the CMS, so one fleet
            can mix hardware and nobody has to think about which is which.
          </p>
          <ul class="mt-10 flex flex-col gap-6">
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
        <!-- The same pairing screen on two shapes of hardware: a wall panel and a portrait
             totem. That is the "any screen" claim, made with a picture. -->
        <div class="reveal lg:col-span-7">
          <div class="flex items-end justify-center gap-6 sm:gap-10">
            <DeviceFrame
              class="w-[62%] max-w-md"
              src="/shots/player-pairing.webp"
              alt="A wall-mounted screen showing the Paskall pairing code"
            >Wall panel</DeviceFrame>
            <DeviceFrame
              class="w-[34%] max-w-[12rem]"
              kind="totem"
              src="/shots/player-pairing-portrait.webp"
              alt="A portrait totem showing the Paskall pairing code"
            >Portrait totem</DeviceFrame>
          </div>
          <p class="mt-6 text-center text-[13px] text-white/60">What a screen shows until you pair it.</p>
        </div>
      </div>
    </div>
  </section>
</template>
