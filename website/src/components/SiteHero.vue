<script setup lang="ts">
import IconArrowForward from '~icons/material-symbols/arrow-forward'

import HeroStage from './HeroStage.vue'

/** What the product does, kept honest: no customer counts we do not have. */
const FACTS = [
  { value: '4K', label: 'Video at full resolution' },
  { value: '30s', label: 'From save to screen' },
  { value: '0', label: 'Network needed to play' },
  { value: '3', label: 'Ways to run a screen' },
]
</script>

<template>
  <section id="top" class="relative">
    <!-- The angled band: colour that ends on a diagonal, so the page below rises into it. -->
    <div class="angled-band absolute inset-x-0 top-0 h-[44rem] sm:h-[50rem]" aria-hidden="true" />

    <div class="relative mx-auto max-w-7xl px-5 pt-28 pb-12 sm:px-8 sm:pt-32">
      <div class="grid items-center gap-8 lg:grid-cols-12">
        <div class="lg:col-span-6">
          <p class="reveal inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-3 py-1 text-[13px] text-white/90 backdrop-blur">
            <span class="size-1.5 rounded-full bg-accent" /> Digital signage, run from one place
          </p>
          <h1 class="reveal mt-6 text-5xl leading-[1.05] text-white sm:text-6xl">
            Every screen you own, <span class="brand-text">playing what you meant.</span>
          </h1>
          <p class="reveal mt-5 text-lg leading-relaxed text-white/80">
            Android boxes, smart TVs and browsers, run as one fleet from a single dashboard.
          </p>
          <div class="reveal mt-8 flex flex-wrap items-center gap-3">
            <a href="#contact" class="inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 text-sm text-brand transition-colors hover:bg-white/90">
              Request access <IconArrowForward class="size-4" />
            </a>
            <a href="#tour" class="inline-flex items-center gap-2 rounded-full border border-white/30 px-5 py-3 text-sm text-white transition-colors hover:bg-white/10">
              See the product
            </a>
          </div>
        </div>

        <!-- The product in one gesture: pick a playlist, the screen changes. -->
        <div class="reveal lg:col-span-6">
          <HeroStage />
        </div>
      </div>
    </div>

    <!-- The numbers strip, across the seam between the band and the page. -->
    <div class="relative mx-auto max-w-7xl px-5 pb-16 sm:px-8">
      <dl class="reveal grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-line bg-line md:grid-cols-4">
        <div v-for="f in FACTS" :key="f.label" class="bg-canvas px-6 py-7">
          <dt class="display text-3xl text-brand">{{ f.value }}</dt>
          <dd class="mt-1 text-[13px] leading-snug text-ink-muted">{{ f.label }}</dd>
        </div>
      </dl>
    </div>
  </section>
</template>
