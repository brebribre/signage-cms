<script setup lang="ts">
import SiteConnect from './SiteConnect.vue'
import SiteDesign from './SiteDesign.vue'
import SitePublish from './SitePublish.vue'
import { useI18n } from '@/i18n'

const { m } = useI18n()
</script>

<template>
  <div class="mx-auto max-w-7xl px-5 pt-20 pb-10 sm:px-8 sm:pt-28">
    <!-- One statement, lead in ink and the rest in grey, in place of a heading and a subtitle. -->
    <h2 class="reveal max-w-4xl text-3xl leading-[1.15] sm:text-5xl sm:leading-[1.1]">
      {{ m.features.lead }} <span class="text-ink-muted">{{ m.features.rest }}</span>
    </h2>
    <div class="mt-14 flex flex-col gap-6 sm:mt-20 sm:gap-8">
      <SiteConnect />
      <SiteDesign />
      <SitePublish />
    </div>
  </div>
</template>
