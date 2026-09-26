<script setup lang="ts">
/**
 * The /how-it-works page, reached from the nav and the footer: the feature cards as a bento,
 * cards of different widths sharing rows on a wide page, in the order a customer meets them:
 * set up the device, connect it, design, publish, and what it runs on. On a phone they stack.
 */
import { watchEffect } from 'vue'

import SiteConnect from './SiteConnect.vue'
import SiteDesign from './SiteDesign.vue'
import SitePlatforms from './SitePlatforms.vue'
import SitePublish from './SitePublish.vue'
import SiteStart from './SiteStart.vue'
import { useI18n } from '@/i18n'

const { m } = useI18n()
// After the i18n module's own title effect, so this page's title wins, in either language.
watchEffect(() => { document.title = m.value.howPage.metaTitle })
const CELL = 'reveal'
</script>

<template>
  <div class="mx-auto max-w-7xl px-5 pb-10 pt-28 sm:px-8 sm:pt-36">
    <h1 class="reveal max-w-3xl text-2xl leading-[1.2] sm:text-4xl sm:leading-[1.15]">
      {{ m.howPage.lead }} <span class="bg-gradient-to-r from-brand-strong to-brand-bright bg-clip-text text-transparent">{{ m.howPage.rest }}</span>
    </h1>
    <div class="mt-10 grid grid-cols-1 gap-4 sm:mt-14 sm:gap-6 lg:grid-cols-3">
      <SiteStart :class="[CELL, 'lg:col-span-3']" />
      <SiteConnect :class="CELL" />
      <SiteDesign :class="[CELL, 'lg:col-span-2']" />
      <SitePublish :class="CELL" />
      <SitePlatforms :class="[CELL, 'lg:col-span-2']" />
    </div>
  </div>
</template>
