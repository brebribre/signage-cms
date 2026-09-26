<script setup lang="ts">
/**
 * Under the hero: what Marien is and what it's for; then how quickly a screen gets going, the How it
 * works cards in a row that scrolls sideways, and a link to the page; then publishing to every
 * screen at once, over the screen wall.
 */
import { ref } from 'vue'
import IconArrow from '~icons/material-symbols/arrow-forward'
import IconBack from '~icons/material-symbols/arrow-back'

import SiteConnect from './SiteConnect.vue'
import SiteDesign from './SiteDesign.vue'
import SitePublish from './SitePublish.vue'
import SiteUses from './SiteUses.vue'
import SiteWall from './SiteWall.vue'
import { useI18n } from '@/i18n'

const { m } = useI18n()
const STATEMENT = 'reveal max-w-3xl text-2xl leading-[1.2] sm:text-4xl sm:leading-[1.15]'
const GRADIENT = 'bg-gradient-to-r from-brand-strong to-brand-bright bg-clip-text text-transparent'

/** The card row, and the arrows beside the heading that move it by about a card. */
const row = ref<HTMLElement>()
function nudge(dir: 1 | -1) {
  const el = row.value
  if (el) el.scrollBy({ left: dir * Math.min(el.clientWidth * 0.8, 480), behavior: 'smooth' })
}
const ARROW = 'flex size-11 items-center justify-center rounded-full bg-white text-ink ring-1 ring-line-strong transition-colors hover:bg-ink hover:text-white'
/** No reveal on each card: a card peeking in from the side counts as off screen, so it would stay
 *  hidden until scrolled to. The row fades in as one instead. */
const CARD = 'w-[85vw] shrink-0 snap-start sm:w-[26rem]'

</script>

<template>
  <div class="mx-auto max-w-7xl px-5 pt-20 pb-10 sm:px-8 sm:pt-28">
    <!-- One statement, lead in ink and the rest in the hero's blue gradient. -->
    <h2 :class="STATEMENT">{{ m.features.lead }} <span :class="GRADIENT">{{ m.features.rest }}</span></h2>
    <!-- What it is for. -->
    <SiteUses />

    <!-- How quickly. -->
    <div class="mt-20 flex items-end justify-between gap-6 sm:mt-28">
      <div>
        <h2 :class="STATEMENT">{{ m.how.lead }} <span :class="GRADIENT">{{ m.how.rest }}</span></h2>
        <a href="/features" class="reveal mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-brand transition-colors hover:text-brand-strong">
          {{ m.design.seeAll }}<IconArrow class="size-4" aria-hidden="true" />
        </a>
      </div>
      <div class="hidden shrink-0 gap-2 sm:flex">
        <button type="button" :class="ARROW" aria-label="Previous" @click="nudge(-1)"><IconBack class="size-5" /></button>
        <button type="button" :class="ARROW" aria-label="Next" @click="nudge(1)"><IconArrow class="size-5" /></button>
      </div>
    </div>
    <!-- The How it works cards in a row that scrolls sideways, out to the window's edges, its first
         card lined up with the heading; the arrows beside the heading move it. -->
    <div
      ref="row"
      class="card-row reveal relative left-1/2 mt-8 flex w-screen -translate-x-1/2 snap-x snap-mandatory gap-4 overflow-x-auto pb-4 [scrollbar-width:none] sm:mt-10 sm:gap-6 [&::-webkit-scrollbar]:hidden"
    >
      <SiteConnect :class="CARD" />
      <SiteDesign :class="CARD" class="sm:w-[40rem]" />
      <SitePublish :class="CARD" />
    </div>
    <a href="/how-it-works" class="reveal mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-brand transition-colors hover:text-brand-strong">
      {{ m.fleet.howLink }}<IconArrow class="size-4" aria-hidden="true" />
    </a>

    <!-- Everywhere at once: a wall of screens, all changed from the CMS. -->
    <h2 :class="STATEMENT" class="mt-20 sm:mt-28">{{ m.fleet.lead }} <span :class="GRADIENT">{{ m.fleet.rest }}</span></h2>
    <SiteWall class="reveal" />
  </div>
</template>
