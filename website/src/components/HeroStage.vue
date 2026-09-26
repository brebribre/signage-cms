<script setup lang="ts">
/**
 * The hero's picture, laid out the way a product-page hero is: the CMS in the middle, standing in
 * a soft dome with thin arcs round it, and four cards floating at its corners, two of them
 * coloured stat cards, one the pairing code, and one a screen playing what the CMS has on air.
 * Pick a playlist in the CMS and the screen changes.
 *
 * Below a wide page there is no room for the screens to float, so the hero shows the Publish
 * scene instead: one totem in front of the CMS, publishing to it, on the sweep of the blues.
 *
 * It cycles on its own so the page shows what it does without being touched, and stops
 * cycling the moment someone picks a playlist themselves, because taking the wheel and then
 * being overridden is the rudest thing an auto-playing demo can do.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import IconBolt from '~icons/material-symbols/bolt'
import IconDevices from '~icons/material-symbols/devices-outline'

import CmsWindow from './CmsWindow.vue'
import PublishScene from './PublishScene.vue'
import ScreenCard from './ScreenCard.vue'
import SlideArt from './SlideArt.vue'
import { SLIDE_COUNT, useSlides } from '@/data/slides'
import { useI18n } from '@/i18n'

const { m } = useI18n()
const slides = useSlides()
/** The fleet the CMS says it is playing on; one of them floats beside it. */
const FLEET = 4

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
  <!-- As wide as the headline's column, so the cards at its corners line up with the words on
       the left and the nav's buttons on the right. -->
  <div class="relative lg:min-h-[34rem]">
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
    <div class="relative mx-auto hidden max-w-[40rem] lg:absolute lg:inset-x-0 lg:bottom-0 lg:block lg:max-w-[34rem] xl:max-w-[40rem]">
      <CmsWindow :active="active" :screens="FLEET" @select="choose" />
    </div>

    <!-- The cards at its corners, on a wide page. -->
    <div class="pointer-events-none absolute inset-0 hidden lg:block">
      <!-- A stat, top left. -->
      <div class="float pointer-events-auto absolute left-0 top-0 w-48 rounded-xl bg-sky-strong p-5 xl:w-56 xl:p-6 shadow-[0_24px_60px_-30px_rgba(0,24,77,0.45)]" style="--float-delay: -1s">
        <IconBolt class="size-8 text-brand-deep" aria-hidden="true" />
        <p class="display mt-6 text-4xl text-brand-deep">{{ m.hero.press.value }}</p>
        <p class="mt-1 text-sm text-brand-deep/75">{{ m.hero.press.label }}</p>
      </div>

      <!-- The pairing code, bottom left. -->
      <div class="float pointer-events-auto absolute bottom-10 left-0 flex w-64 xl:left-10 xl:w-72 items-center gap-4 rounded-xl bg-white p-3 shadow-[0_24px_60px_-28px_rgba(0,24,77,0.45)] ring-1 ring-line" style="--float-delay: -3s">
        <div class="h-24 w-20 shrink-0 overflow-hidden rounded-lg ring-1 ring-line">
          <SlideArt :slide="slides[3]" thumb />
        </div>
        <div class="min-w-0">
          <p class="text-sm leading-snug text-ink">{{ m.hero.pair }}</p>
          <p class="mt-2.5 inline-block rounded-md bg-brand-deep px-3 py-1 font-mono text-xs tracking-[0.2em] text-white">K7P 2QX</p>
        </div>
      </div>

      <!-- A screen playing what the CMS has on air, top right. -->
      <div class="float pointer-events-auto absolute -top-16 right-6 w-36 xl:right-10 xl:w-40" style="--float-delay: -2s">
        <ScreenCard :active="active" :name="m.hero.screens[2].name" :kind="m.hero.screens[2].kind" portrait />
      </div>

      <!-- A stat, bottom right. -->
      <div class="float pointer-events-auto absolute bottom-6 right-0 w-48 rounded-xl bg-brand-bright p-5 text-white xl:w-52 xl:p-6 shadow-[0_24px_60px_-30px_rgba(0,24,77,0.6)]" style="--float-delay: -4s">
        <IconDevices class="size-8" aria-hidden="true" />
        <p class="display mt-5 text-3xl leading-tight">{{ m.hero.any.value }}</p>
        <p class="mt-1 text-sm text-white/85">{{ m.hero.any.label }}</p>
      </div>
    </div>
  </div>
</template>
