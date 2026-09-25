<script setup lang="ts">
import HeroStage from './HeroStage.vue'
import { useI18n } from '@/i18n'

const { m } = useI18n()
</script>

<template>
  <section id="top" class="relative overflow-hidden bg-canvas pt-28 sm:pt-36">
    <!-- The wave across the top right. -->
    <div class="hero-wave pointer-events-none" aria-hidden="true" />

    <div class="relative mx-auto max-w-7xl px-5 sm:px-8">
      <div class="mx-auto max-w-3xl text-center">
        <h1 class="reveal text-5xl leading-[1.05] text-ink sm:text-6xl lg:text-7xl">
          {{ m.hero.title }}
        </h1>
        <p class="reveal mx-auto mt-6 max-w-lg text-[15px] leading-relaxed text-ink-muted sm:text-base">
          {{ m.hero.subtitle }}
        </p>
        <div class="reveal mt-9 flex flex-wrap items-center justify-center gap-3">
          <a href="#contact" class="rounded-full bg-brand-deep px-6 py-3.5 text-sm font-medium text-white transition-colors hover:bg-brand">
            {{ m.hero.cta }}
          </a>
        </div>
      </div>

      <div class="reveal mt-14 sm:mt-10">
        <HeroStage />
      </div>
    </div>
  </section>
</template>
