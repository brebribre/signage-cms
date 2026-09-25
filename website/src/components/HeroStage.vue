<script setup lang="ts">
/**
 * The hero's picture: the CMS in the middle, standing in a soft dome, and the screens it runs
 * floating round it. Pick a playlist in the CMS and every screen changes.
 *
 * Below a wide page there is no room for the screens to float, so the hero shows the Publish
 * scene instead: one totem in front of the CMS, publishing to it, on the sweep of the blues.
 *
 * It cycles on its own so the page shows what it does without being touched, and stops
 * cycling the moment someone picks a playlist themselves, because taking the wheel and then
 * being overridden is the rudest thing an auto-playing demo can do.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import CmsWindow from './CmsWindow.vue'
import PublishScene from './PublishScene.vue'
import ScreenCard from './ScreenCard.vue'
import { SLIDE_COUNT } from '@/data/slides'
import { useI18n } from '@/i18n'

/** Where each screen floats round the CMS, on a wide page. */
const PLACES = [
  { pos: 'lg:left-0 lg:top-10 lg:w-56', delay: 0 },
  { portrait: true, pos: 'lg:left-16 lg:bottom-6 lg:w-36', delay: 160 },
  { portrait: true, pos: 'lg:right-14 lg:top-0 lg:w-36', delay: 320 },
  { pos: 'lg:right-0 lg:bottom-16 lg:w-56', delay: 480 },
]
const { m } = useI18n()
const SCREENS = computed(() => PLACES.map((p, i) => ({ ...p, ...m.value.hero.screens[i] })))

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
  timer = window.setInterval(() => { active.value = (active.value + 1) % SLIDE_COUNT }, CYCLE_MS)
})
onBeforeUnmount(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <div class="relative mx-auto max-w-6xl lg:min-h-[34rem]">
    <!-- The dome and its rings, anchored to the floor the CMS stands on. -->
    <div class="pointer-events-none absolute inset-x-0 bottom-0 hidden justify-center overflow-hidden lg:flex" aria-hidden="true">
      <div class="relative h-[21rem] w-[44rem] lg:h-[24rem] lg:w-[50rem]">
        <div class="hero-ring absolute -inset-x-40 -top-40 bottom-0 rounded-t-full border-b-0" />
        <div class="hero-ring absolute -inset-x-20 -top-20 bottom-0 rounded-t-full border-b-0" />
        <div class="hero-dome absolute inset-0 rounded-t-full" />
      </div>
    </div>

    <!-- Below a wide page: the Publish scene, on a sweep, running off the foot of the hero and
         (on a phone) its right edge. On a tablet it is centred and fades out on the right. -->
    <div class="@container relative -mx-5 sm:-mx-8 lg:hidden">
      <div class="card-sweep pointer-events-none absolute -right-[30%] -left-[10%] top-[6%] h-[86%] -rotate-[22deg] rounded-[50%]" aria-hidden="true" />
      <PublishScene class="relative sm:mx-auto sm:max-w-xl sm:[mask-image:linear-gradient(90deg,#000_82%,transparent)]" />
    </div>

    <!-- The CMS, centre stage, on a wide page. -->
    <div class="relative mx-auto hidden max-w-[40rem] lg:absolute lg:inset-x-0 lg:bottom-0 lg:block">
      <CmsWindow :active="active" :screens="SCREENS.length" @select="choose" />
    </div>

    <!-- The screens it runs, floating round it where there is room for them. -->
    <ul class="hidden lg:block">
      <li
        v-for="(s, i) in SCREENS" :key="i"
        class="float lg:absolute" :class="s.pos" :style="{ '--float-delay': `${-i * 1.4}s` }"
      >
        <ScreenCard :active="active" :name="s.name" :kind="s.kind" :portrait="s.portrait" :delay="s.delay" />
      </li>
    </ul>
  </div>
</template>
