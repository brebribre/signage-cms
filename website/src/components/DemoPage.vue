<script setup lang="ts">
/**
 * The /demo page, reached from the hero's See demo button. The real thing, filmed: the CMS on a
 * laptop beside a TV on a desk, recorded at the same time, so every click on the left is seen
 * landing on the screen on the right. The video's own dark frame is the card's colour, so its
 * edges disappear into it.
 */
import { watchEffect } from 'vue'

import { useI18n } from '@/i18n'

const { m } = useI18n()
// Runs after the i18n module's own title effect, so this page's title wins, in either language.
watchEffect(() => { document.title = m.value.demo.metaTitle })
</script>

<template>
  <section id="demo" class="mx-auto max-w-7xl px-5 pb-20 pt-28 sm:px-8 sm:pb-28 sm:pt-36">
    <div class="reveal mx-auto max-w-3xl text-center">
      <h1 class="text-4xl leading-[1.1] sm:text-5xl lg:text-6xl lg:leading-[1.05]">
        {{ m.demo.lead }} <span class="text-ink-muted">{{ m.demo.rest }}</span>
      </h1>
    </div>

    <div class="reveal mt-10 overflow-hidden rounded-[1.5rem] bg-[#111317] p-2 shadow-[0_40px_100px_-40px_rgba(0,24,77,0.45)] sm:mt-12 sm:rounded-[2rem] sm:p-3">
      <video
        class="block aspect-[1920/744] w-full rounded-[1rem] sm:rounded-[1.4rem]"
        src="/media/paskall-demo.mp4"
        poster="/media/paskall-demo-poster.webp"
        :aria-label="m.demo.videoLabel"
        controls
        muted
        playsinline
        preload="metadata"
      />
    </div>
    <p class="reveal mt-4 flex justify-between gap-4 px-1 text-sm text-ink-muted">
      <span>{{ m.demo.left }}</span>
      <span class="text-right">{{ m.demo.right }}</span>
    </p>
  </section>
</template>
