<script setup lang="ts">
import BrowserFrame from './BrowserFrame.vue'

const STOPS = [
  {
    eyebrow: 'Scene editor', title: 'Design at the screen’s real size.',
    text: 'Pick a screen and its exact shape becomes your canvas.',
    src: '/shots/scene.webp', label: 'paskall · Scene', flip: false,
  },
  {
    eyebrow: 'Campaigns', title: 'Say when, and it happens.',
    text: 'A loop all day, or a week of rules. The timeline shows both.',
    src: '/shots/campaign.webp', label: 'paskall · Campaign', flip: true,
  },
  {
    eyebrow: 'Screens', title: 'Every screen, without walking to it.',
    text: 'What is playing, why, and anything that went wrong.',
    src: '/shots/screens.webp', label: 'paskall · Screens', flip: false,
  },
  {
    eyebrow: 'Playlists', title: 'Preview before you publish.',
    text: 'Saving something already on air asks first, and names the screens.',
    src: '/shots/playlist.webp', label: 'paskall · Playlist', flip: true,
  },
]
</script>

<template>
  <section id="tour" class="bg-page py-20 sm:py-28">
    <div class="mx-auto max-w-7xl px-5 sm:px-8">
      <div class="reveal max-w-2xl">
        <p class="text-[13px] font-medium uppercase tracking-wider text-brand">A look inside</p>
        <h2 class="mt-3 text-3xl leading-tight sm:text-4xl">Four screens you’ll live in.</h2>
      </div>
      <div class="mt-16 flex flex-col gap-20 sm:gap-28">
        <div v-for="s in STOPS" :key="s.title" class="reveal grid items-center gap-8 lg:grid-cols-12 lg:gap-14">
          <div class="lg:col-span-4" :class="s.flip && 'lg:order-2'">
            <p class="text-[13px] font-medium uppercase tracking-wider text-brand">{{ s.eyebrow }}</p>
            <h3 class="mt-3 text-2xl leading-tight sm:text-3xl">{{ s.title }}</h3>
            <p class="mt-3 leading-relaxed text-ink-muted">{{ s.text }}</p>
          </div>
          <div class="lg:col-span-8" :class="s.flip && 'lg:order-1'">
            <BrowserFrame :src="s.src" :alt="s.title" :label="s.label" />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
