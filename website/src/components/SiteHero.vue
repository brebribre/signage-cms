<script setup lang="ts">
import IconArrowForward from '~icons/material-symbols/arrow-forward'

import BrowserFrame from './BrowserFrame.vue'

/** The numbers a signage buyer actually weighs, kept honest: these are what the product does,
 *  not customer counts we don't have. */
const FACTS = [
  { value: '4K', label: 'Video, kept at full resolution' },
  { value: '~30s', label: 'From save to every screen' },
  { value: '0', label: 'Network needed to keep playing' },
  { value: '3', label: 'Players: Android, smart TV, browser' },
]
</script>

<template>
  <section id="top" class="relative">
    <!-- The angled band: colour that ends on a diagonal, so the page below rises into it. -->
    <div class="angled-band absolute inset-x-0 top-0 h-[42rem] sm:h-[46rem]" aria-hidden="true" />

    <div class="relative mx-auto max-w-7xl px-5 pt-28 pb-16 sm:px-8 sm:pt-36">
      <div class="grid items-center gap-12 lg:grid-cols-12 lg:gap-8">
        <!-- Left-aligned, the way an infrastructure page opens: claim, sentence, two actions. -->
        <div class="lg:col-span-5">
          <p class="reveal inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-3 py-1 text-[13px] text-white/90 backdrop-blur">
            <span class="size-1.5 rounded-full bg-accent" /> Digital signage infrastructure
          </p>
          <h1 class="reveal mt-6 text-5xl leading-[1.05] text-white sm:text-6xl">
            Every screen you own, <span class="brand-text">playing what you meant.</span>
          </h1>
          <p class="reveal mt-6 text-lg leading-relaxed text-white/80">
            Paskall turns Android boxes, smart TVs and any browser into one fleet you run from a single
            dashboard. Build scenes, schedule campaigns, and let the screens look after themselves.
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

        <!-- The product, beside the words rather than beneath them, tipped slightly so it reads
             as a thing on a desk instead of a flat image. -->
        <div class="reveal lg:col-span-7">
          <div class="lg:[transform:perspective(2000px)_rotateY(-7deg)_rotateX(2deg)] lg:origin-left">
            <BrowserFrame src="/shots/overview.webp" alt="The Paskall overview: screens, campaigns, what is playing now, reviews and errors" label="paskall · Overview" />
          </div>
        </div>
      </div>
    </div>

    <!-- The numbers strip, sitting across the seam between the band and the page. -->
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
