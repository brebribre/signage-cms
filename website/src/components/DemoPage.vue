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
        {{ m.demo.title }}
      </h1>
    </div>

    <!-- Phones get the portrait cut, the CMS above the screen, which fills their width; wider
         pages get the side-by-side one. Neither loads until play is pressed, so the hidden one
         costs nothing. -->
    <div class="reveal mx-auto mt-10 max-w-md overflow-hidden rounded-[1.5rem] bg-[#111317] p-2 shadow-[0_40px_100px_-40px_rgba(0,24,77,0.45)] sm:hidden">
      <video
        class="block aspect-[9/16] w-full rounded-[1rem]"
        src="/media/paskall-demo-portrait.mp4"
        poster="/media/paskall-demo-portrait-poster.webp"
        :aria-label="m.demo.videoLabel"
        controls
        playsinline
        preload="none"
      />
    </div>
    <div class="reveal mt-12 hidden overflow-hidden rounded-[2rem] bg-[#111317] p-3 shadow-[0_40px_100px_-40px_rgba(0,24,77,0.45)] sm:block">
      <video
        class="block aspect-[1920/744] w-full rounded-[1.4rem]"
        src="/media/paskall-demo.mp4"
        poster="/media/paskall-demo-poster.webp"
        :aria-label="m.demo.videoLabel"
        controls
        playsinline
        preload="none"
      />
    </div>
    <!-- The portrait cut names its two halves on the video itself. -->
    <p class="reveal mt-4 hidden justify-between gap-4 px-1 text-sm text-ink-muted sm:flex">
      <span>{{ m.demo.left }}</span>
      <span class="text-right">{{ m.demo.right }}</span>
    </p>
  </section>
</template>
