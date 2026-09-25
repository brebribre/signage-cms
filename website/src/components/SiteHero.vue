<script setup lang="ts">
import IconPlay from '~icons/material-symbols/play-circle-outline'

import HeroStage from './HeroStage.vue'
import { useI18n } from '@/i18n'

const { m } = useI18n()
</script>

<template>
  <section id="top" class="relative overflow-hidden bg-canvas pt-28 sm:pt-36">
    <!-- The wave across the top right. -->
    <div class="hero-wave pointer-events-none" aria-hidden="true" />

    <div class="relative mx-auto max-w-7xl px-5 sm:px-8">
      <div class="mx-auto max-w-4xl text-left sm:text-center">
        <!-- One statement: the claim in ink, what it covers in brand blue, at the same size,
             rather than a headline over small print. Blue rather than grey, which reads muddy
             against the white and the wave. On a phone it sits flush left over full-width
             buttons, the way a phone page reads top to bottom. -->
        <h1 class="reveal text-[2.5rem] leading-[1.08] sm:leading-[1.1] text-ink sm:text-6xl lg:text-7xl lg:leading-[1.03]">
          {{ m.hero.title }} <span class="text-brand">{{ m.hero.subtitle }}</span>
        </h1>
        <div class="reveal mt-9 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-center">
          <a href="#contact" class="rounded-lg bg-brand-deep px-6 py-4 text-center text-base font-medium sm:rounded-full sm:py-3.5 sm:text-sm text-white transition-colors hover:bg-brand">
            {{ m.hero.cta }}
          </a>
          <a href="/demo" class="inline-flex items-center justify-center gap-2 rounded-lg bg-white/80 px-6 py-4 text-base font-medium sm:rounded-full sm:py-3.5 sm:text-sm text-ink ring-1 ring-ink/70 backdrop-blur transition-colors hover:bg-ink hover:text-white">
            <IconPlay class="size-5" />
            {{ m.hero.demo }}
          </a>
        </div>
      </div>

      <div class="reveal mt-14 sm:mt-10">
        <HeroStage />
      </div>
    </div>
  </section>
</template>
