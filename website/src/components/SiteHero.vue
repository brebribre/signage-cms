<script setup lang="ts">
import HeroStage from './HeroStage.vue'
</script>

<template>
  <section id="top" class="brand-sweep relative overflow-hidden pt-28 sm:pt-36">
    <!-- The background's slow life: two drifting glows and rings pulsing off the floor. -->
    <div class="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      <div class="hero-glow hero-glow-a -left-40 -top-40 size-[34rem] bg-accent/30" />
      <div class="hero-glow hero-glow-b -right-32 top-1/4 size-[30rem] bg-[#7fb6ff]/30" />
      <div class="hero-pulse" />
      <div class="hero-pulse" style="--pulse-delay: -3s" />
      <div class="hero-pulse" style="--pulse-delay: -6s" />
    </div>

    <div class="relative mx-auto max-w-7xl px-5 sm:px-8">
      <div class="mx-auto max-w-3xl text-center">
        <h1 class="reveal text-5xl leading-[1.05] text-white sm:text-6xl lg:text-7xl">
          Meet the smart way to manage your screens
        </h1>
        <p class="reveal mx-auto mt-6 max-w-lg text-[15px] leading-relaxed text-white/75 sm:text-base">
          Pictures, videos and live websites on digital signage, smart TVs and Android boxes, all
          run as one fleet from a single dashboard.
        </p>
        <div class="reveal mt-9 flex flex-wrap items-center justify-center gap-3">
          <a href="#contact" class="rounded-full bg-white px-6 py-3.5 text-sm font-medium text-brand-deep transition-colors hover:bg-sky">
            Request access
          </a>
        </div>
      </div>

      <div class="reveal mt-14 sm:mt-10">
        <HeroStage />
      </div>
    </div>
  </section>
</template>
