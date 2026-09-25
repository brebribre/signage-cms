<script setup lang="ts">
import HeroStage from './HeroStage.vue'
</script>

<template>
  <section id="top" class="relative overflow-hidden pt-28 sm:pt-36">
    <div class="mx-auto max-w-7xl px-5 sm:px-8">
      <div class="mx-auto max-w-3xl text-center">
        <h1 class="reveal text-5xl leading-[1.05] text-ink sm:text-6xl lg:text-7xl">
          Meet the calm way to run every screen
        </h1>
        <p class="reveal mx-auto mt-6 max-w-xl text-lg leading-relaxed text-ink-muted">
          Playlists, campaigns and live websites on Android boxes, smart TVs and browsers, all run
          as one fleet from a single dashboard.
        </p>
        <div class="reveal mt-9 flex flex-wrap items-center justify-center gap-3">
          <a href="#contact" class="rounded-full bg-brand-deep px-6 py-3.5 text-sm font-medium text-white transition-colors hover:bg-brand">
            Request access. It's free to try
          </a>
          <a href="#connect" class="rounded-full border border-ink/80 px-6 py-3.5 text-sm font-medium text-ink transition-colors hover:bg-ink hover:text-white">
            See how it works
          </a>
        </div>
      </div>

      <div class="reveal mt-14 sm:mt-10">
        <HeroStage />
      </div>
    </div>
  </section>
</template>
