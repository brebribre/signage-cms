<script setup lang="ts">
/**
 * The /demo page, reached from the hero's See demo button. The real thing, recorded: the CMS
 * beside a screen running the web player, captured together, so every click on the left is seen
 * landing on the screen on the right — from a screen showing its code to it playing a playlist.
 */
import { watchEffect } from 'vue'

import { track } from '@/composables/useAnalytics'
import { useI18n } from '@/i18n'

const { m } = useI18n()
/** The demo plays at 1.5×: it is a recording of real clicks, and at 1× the waits drag. Set as
 *  the default rate too, so it survives the browser resetting the rate when the video loads. */
const SPEED = 1.5
function fast(e: Event) {
  const v = e.target as HTMLVideoElement
  v.defaultPlaybackRate = SPEED
  v.playbackRate = SPEED
}
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
    <div class="reveal mx-auto mt-10 max-w-md overflow-hidden rounded-xl bg-[#111317] p-2 shadow-[0_40px_100px_-40px_rgba(0,24,77,0.45)] sm:hidden">
      <video
        class="block aspect-[9/16] w-full rounded-lg"
        src="/media/marien-demo-portrait.mp4"
        @play.once="track('demo_video_play', { cut: 'portrait' })"
        @loadedmetadata="fast"
        poster="/media/marien-demo-portrait-poster.webp"
        :aria-label="m.demo.videoLabel"
        controls
        playsinline
        preload="none"
      />
    </div>
    <div class="reveal mt-12 hidden overflow-hidden rounded-2xl bg-[#111317] p-3 shadow-[0_40px_100px_-40px_rgba(0,24,77,0.45)] sm:block">
      <video
        class="block aspect-video w-full rounded-xl"
        src="/media/marien-demo.mp4"
        @play.once="track('demo_video_play', { cut: 'wide' })"
        @loadedmetadata="fast"
        poster="/media/marien-demo-poster.webp"
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
