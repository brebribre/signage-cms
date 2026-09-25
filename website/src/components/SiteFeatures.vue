<script setup lang="ts">
/**
 * The features, as a bento: cards of different widths sharing rows on a wide page, the way a
 * product page packs a lot into little height. On a phone the same cards sit in one row that
 * scrolls sideways, each card most of the screen wide with the next one peeking in, so the
 * section is one card tall instead of four.
 *
 * The reveal is on the row, not the cards: a card waiting off to the side of a phone's
 * scroller never crosses the viewport, and would never be told it had arrived.
 */
import SiteConnect from './SiteConnect.vue'
import SiteDesign from './SiteDesign.vue'
import SitePlatforms from './SitePlatforms.vue'
import SitePublish from './SitePublish.vue'
import { useI18n } from '@/i18n'

const { m } = useI18n()
const CELL = 'w-[86%] shrink-0 snap-center sm:w-[62%] lg:w-auto'
</script>

<template>
  <div class="mx-auto max-w-7xl px-5 pt-20 pb-10 sm:px-8 sm:pt-28">
    <!-- One statement, lead in ink and the rest in grey, in place of a heading and a subtitle. -->
    <h2 class="reveal max-w-4xl text-3xl leading-[1.15] sm:text-5xl sm:leading-[1.1]">
      {{ m.features.lead }} <span class="text-ink-muted">{{ m.features.rest }}</span>
    </h2>
    <div
      class="reveal -mx-5 mt-10 flex snap-x snap-mandatory gap-4 overflow-x-auto px-5 pb-2 [scrollbar-width:none] sm:-mx-8 sm:mt-14 sm:px-8 lg:mx-0 lg:grid lg:grid-cols-3 lg:gap-6 lg:overflow-visible lg:px-0 lg:pb-0 [&::-webkit-scrollbar]:hidden"
    >
      <!-- In the order a customer meets them: connect, design, publish, and what it runs on. -->
      <SiteConnect :class="CELL" />
      <SiteDesign :class="[CELL, 'lg:col-span-2']" />
      <SitePublish :class="CELL" />
      <SitePlatforms :class="[CELL, 'lg:col-span-2']" />
    </div>
  </div>
</template>
