<script setup lang="ts">
import IconPlay from '~icons/material-symbols/play-circle-outline'

import HeroStage from './HeroStage.vue'
import { track } from '@/composables/useAnalytics'
import { useI18n } from '@/i18n'

const { m } = useI18n()
</script>

<template>
  <section id="top" class="relative overflow-hidden bg-canvas pt-28 sm:pt-36">
    <!-- The wave across the top right. -->
    <div class="hero-wave pointer-events-none" aria-hidden="true" />

    <div class="relative mx-auto max-w-7xl px-5 sm:px-8">
      <div class="max-w-5xl text-left">
        <!-- One statement: the claim in ink, what it covers in the brand gradient (as the Instagram posts set it), at the same size, rather
             than a headline over small print, the way every section below states itself.
             Flush left at every width, with the buttons under it: full width and stacked on a
             phone, side by side from there up. -->
        <h1 class="reveal text-[2.125rem] leading-[1.1] text-ink sm:text-5xl lg:text-6xl lg:leading-[1.05]">
          {{ m.hero.title }} <span class="bg-gradient-to-r from-brand-strong to-brand-bright bg-clip-text text-transparent">{{ m.hero.subtitle }}</span>
        </h1>
        <div class="reveal mt-9 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
          <a href="#contact" @click="track('request_access_click', { location: 'hero' })" class="rounded-lg bg-action px-6 py-4 text-center text-base font-medium sm:py-3.5 sm:text-sm text-white transition-colors hover:bg-action-hover">
            {{ m.hero.cta }}
          </a>
          <a href="/demo" @click="track('see_demo_click', { location: 'hero' })" class="inline-flex items-center justify-center gap-2 rounded-lg bg-white/80 px-6 py-4 text-base font-medium sm:py-3.5 sm:text-sm text-ink ring-1 ring-ink/70 backdrop-blur transition-colors hover:bg-ink hover:text-white">
            <IconPlay class="size-5" />
            {{ m.hero.demo }}
          </a>
        </div>
      </div>

      <div class="reveal mt-14 sm:mt-10">
        <HeroStage />
      </div>
    </div>

    <!-- The second wave, over the picture, covering the right end of the CMS window. -->
    <div class="hero-wave-low pointer-events-none hidden sm:block" aria-hidden="true" />
  </section>
</template>
