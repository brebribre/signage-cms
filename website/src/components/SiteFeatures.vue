<script setup lang="ts">
import SiteConnect from './SiteConnect.vue'
import SiteDesign from './SiteDesign.vue'
import SitePublish from './SitePublish.vue'
import { useI18n } from '@/i18n'

const { m } = useI18n()
</script>

<template>
  <div class="mx-auto max-w-7xl px-5 pt-20 pb-10 sm:px-8 sm:pt-28">
    <div class="reveal mx-auto max-w-2xl text-center">
      <h2 class="text-4xl leading-[1.1] sm:text-5xl">{{ m.features.title }}</h2>
      <p class="mt-5 text-lg text-ink-muted">{{ m.features.subtitle }}</p>
    </div>
    <div class="mt-14 flex flex-col gap-6 sm:mt-20 sm:gap-8">
      <SiteConnect />
      <SiteDesign />
      <SitePublish />
    </div>
  </div>
</template>
