<script setup lang="ts">
/**
 * The hero's picture: the CMS in the middle, standing in a soft dome, and the screens it runs
 * floating round it. Pick a playlist in the CMS and every screen changes.
 *
 * It cycles on its own so the page shows what it does without being touched, and stops
 * cycling the moment someone picks a playlist themselves, because taking the wheel and then
 * being overridden is the rudest thing an auto-playing demo can do.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

import CmsWindow from './CmsWindow.vue'
import ScreenCard from './ScreenCard.vue'
import { SLIDES } from '@/data/slides'

/** Where each screen floats round the CMS. Only on a wide page; a phone shows the CMS alone. */
const SCREENS = [
  { name: 'Lobby TV', kind: 'Android box', pos: 'lg:left-0 lg:top-10 lg:w-56', delay: 0 },
  { name: 'Entrance totem', kind: 'Smart TV', portrait: true, pos: 'lg:left-16 lg:bottom-6 lg:w-36', delay: 160 },
  { name: 'Reception', kind: 'Android box', portrait: true, pos: 'lg:right-14 lg:top-0 lg:w-36', delay: 320 },
  { name: 'Cafe screen', kind: 'Browser', pos: 'lg:right-0 lg:bottom-16 lg:w-56', delay: 480 },
]

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
</script>

<template>
  <div class="relative mx-auto max-w-6xl lg:min-h-[34rem]">
    <!-- The dome and its rings, anchored to the floor the CMS stands on. -->
    <div class="pointer-events-none absolute inset-x-0 bottom-0 hidden justify-center overflow-hidden sm:flex" aria-hidden="true">
      <div class="relative h-[21rem] w-[44rem] lg:h-[24rem] lg:w-[50rem]">
        <div class="hero-ring hero-ring-inverse absolute -inset-x-40 -top-40 bottom-0 rounded-t-full border-b-0" />
        <div class="hero-ring hero-ring-inverse absolute -inset-x-20 -top-20 bottom-0 rounded-t-full border-b-0" />
        <div class="hero-dome absolute inset-0 rounded-t-full" />
      </div>
    </div>

    <!-- The CMS, centre stage. On a phone it is the whole picture, cropped to its top half so
         it runs off the foot of the hero the way it stands in the dome on a wide page. -->
    <div class="relative mx-auto max-h-[17rem] max-w-[40rem] overflow-hidden pt-4 sm:max-h-[24rem] lg:absolute lg:inset-x-0 lg:bottom-0 lg:max-h-none">
      <CmsWindow :active="active" :screens="SCREENS.length" @select="choose" />
    </div>

    <!-- The screens it runs, floating round it where there is room for them. -->
    <ul class="hidden lg:block">
      <li
        v-for="(s, i) in SCREENS" :key="s.name"
        class="float lg:absolute" :class="s.pos" :style="{ '--float-delay': `${-i * 1.4}s` }"
      >
        <ScreenCard :active="active" :name="s.name" :kind="s.kind" :portrait="s.portrait" :delay="s.delay" />
      </li>
    </ul>
  </div>
</template>
