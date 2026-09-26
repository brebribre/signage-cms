<script setup lang="ts">
/**
 * The features, as a bento: cards of different widths sharing rows on a wide page, the way a
 * product page packs a lot into little height. On a phone they simply stack.
 */
import SiteConnect from './SiteConnect.vue'
import SiteDesign from './SiteDesign.vue'
import SitePlatforms from './SitePlatforms.vue'
import SitePublish from './SitePublish.vue'
import SiteStart from './SiteStart.vue'
import SiteUses from './SiteUses.vue'
import { useI18n } from '@/i18n'

const { m } = useI18n()
const CELL = 'reveal'
</script>

<template>
  <div class="mx-auto max-w-7xl px-5 pt-20 pb-10 sm:px-8 sm:pt-28">
    <!-- One statement, lead in ink and the rest in the hero's blue gradient. -->
    <h2 class="reveal max-w-3xl text-2xl leading-[1.2] sm:text-4xl sm:leading-[1.15]">
      {{ m.features.lead }} <span class="bg-gradient-to-r from-brand-strong to-brand-bright bg-clip-text text-transparent">{{ m.features.rest }}</span>
    </h2>
    <!-- What it is for, before how it works. -->
    <SiteUses />
    <!-- The feature cards, under their own title. -->
    <h2 class="reveal mt-20 text-3xl leading-[1.15] sm:mt-28 sm:text-5xl sm:leading-[1.1]">{{ m.how.title }}</h2>
    <div class="mt-10 grid grid-cols-1 gap-4 sm:mt-14 sm:gap-6 lg:grid-cols-3">
      <!-- In the order a customer meets them: get started, connect, design, publish, and what it
           runs on. -->
      <SiteStart :class="[CELL, 'lg:col-span-3']" />
      <SiteConnect :class="CELL" />
      <SiteDesign :class="[CELL, 'lg:col-span-2']" />
      <SitePublish :class="CELL" />
      <SitePlatforms :class="[CELL, 'lg:col-span-2']" />
    </div>
  </div>
</template>
