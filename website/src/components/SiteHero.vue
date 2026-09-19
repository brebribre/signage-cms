<script setup lang="ts">
import IconArrowForward from '~icons/material-symbols/arrow-forward'
import IconPlayArrow from '~icons/material-symbols/play-arrow'

import BrowserFrame from './BrowserFrame.vue'
</script>

<template>
  <section id="top" class="relative overflow-hidden">
    <div class="dot-grid absolute inset-0 -z-10" aria-hidden="true" />
    <!-- A wash of the brand gradient behind the hero, fading before the fold. -->
    <div class="absolute inset-x-0 top-0 -z-10 h-[46rem] bg-[radial-gradient(60%_50%_at_50%_0%,rgba(0,118,221,0.18),transparent_70%)]" aria-hidden="true" />

    <div class="mx-auto max-w-6xl px-5 pt-16 pb-10 sm:px-8 sm:pt-24">
      <div class="mx-auto max-w-3xl text-center">
        <p class="reveal inline-flex items-center gap-2 rounded-full border border-line bg-canvas px-3 py-1 text-[13px] text-ink-muted">
          <span class="size-1.5 rounded-full bg-brand-bright" /> Digital signage, run from one place
        </p>
        <h1 class="reveal mt-6 text-5xl leading-[1.05] sm:text-6xl md:text-7xl">
          Every screen you own,<br /><span class="brand-text">playing what you meant.</span>
        </h1>
        <p class="reveal mt-6 text-lg text-ink-muted sm:text-xl">
          Paskall turns Android boxes, smart TVs and any browser into a fleet of screens you run from a
          single calm dashboard. Build scenes, schedule campaigns, and let the screens look after themselves.
        </p>
        <div class="reveal mt-8 flex flex-wrap items-center justify-center gap-3">
          <a href="#contact" class="inline-flex items-center gap-2 rounded-full bg-brand px-5 py-3 text-sm text-ink-inverse transition-colors hover:bg-hover">
            Request access <IconArrowForward class="size-4" />
          </a>
          <a href="#how" class="inline-flex items-center gap-2 rounded-full border border-line-strong px-5 py-3 text-sm text-ink transition-colors hover:border-ink">
            <IconPlayArrow class="size-4" /> See how it works
          </a>
        </div>
      </div>

      <div class="reveal relative mx-auto mt-14 max-w-5xl">
        <BrowserFrame src="/shots/overview.webp" alt="The Paskall overview: screens, campaigns, what is playing now, reviews and errors" label="paskall · Overview" />
      </div>

      <ul class="reveal mx-auto mt-10 flex max-w-4xl flex-wrap items-center justify-center gap-x-8 gap-y-3 text-[13px] text-ink-subtle">
        <li>Android boxes</li><li class="hidden sm:inline">·</li>
        <li>Samsung and LG smart TVs</li><li class="hidden sm:inline">·</li>
        <li>Any screen with a browser</li><li class="hidden sm:inline">·</li>
        <li>Portrait and landscape</li><li class="hidden sm:inline">·</li>
        <li>Up to 4K</li>
      </ul>
    </div>
  </section>
</template>
