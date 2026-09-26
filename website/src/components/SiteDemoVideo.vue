<script setup lang="ts">
/**
 * The home page's demo: a short silent recording of the CMS beside a screen running the web
 * player, from pairing to deploying, in the same thin black bezel as the signage in the hero. It loops on its own
 * like a moving picture, muted, and only while it's on screen; nothing is downloaded until a
 * visitor scrolls near it. A visitor who asked for less motion gets the still and the controls
 * instead, and plays it themselves.
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'

import { useI18n } from '@/i18n'

const { m } = useI18n()
const video = ref<HTMLVideoElement>()
const still = ref(false)

onMounted(() => {
  const v = video.value
  if (!v) return
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { still.value = true; return }
  const io = new IntersectionObserver(
    ([e]) => { if (e.isIntersecting) v.play().catch(() => { still.value = true }); else v.pause() },
    { threshold: 0.3 },
  )
  io.observe(v)
  onBeforeUnmount(() => io.disconnect())
})
</script>

<template>
  <section id="see-demo" class="mx-auto max-w-7xl px-5 pt-20 sm:px-8 sm:pt-28">
    <h2 class="reveal text-3xl leading-[1.15] sm:text-5xl sm:leading-[1.1]">{{ m.seeDemo.title }}</h2>

    <!-- The bezel: the signage's black frame, thin, with the picture set square in it. -->
    <div class="reveal mt-10 rounded-xl bg-gradient-to-b from-[#1b1e24] to-[#0f1115] p-1.5 shadow-[0_40px_90px_-40px_rgba(0,24,77,0.55),inset_0_1px_0_rgba(255,255,255,0.12)] ring-1 ring-black/60 sm:mt-12 sm:p-2.5">
      <video
        ref="video"
        class="block aspect-video w-full bg-[#0b1a4a] shadow-[0_0_0_1px_rgba(0,24,77,0.12)]"
        src="/media/marien-demo-loop.mp4"
        poster="/media/marien-demo-loop-poster.webp"
        :aria-label="m.seeDemo.videoLabel"
        :controls="still"
        muted
        loop
        playsinline
        preload="none"
      />
    </div>
  </section>
</template>
