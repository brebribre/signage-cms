<script setup lang="ts">
import BrowserFrame from './BrowserFrame.vue'

const STOPS = [
  {
    eyebrow: 'Scene editor', title: 'Design on the screen’s own shape.',
    text: 'Pick the screen you are designing for and its exact size becomes your canvas. Drop in media from the library, add a headline, blur the background behind a portrait photo. Live elements — video and websites — are budgeted, so a scene never asks a box for more than it can decode.',
    src: '/shots/scene.webp', label: 'paskall · Scene', flip: false,
  },
  {
    eyebrow: 'Campaigns', title: 'Say when, and it happens.',
    text: 'A campaign puts playlists on screens: one loop all day, or a week of rules with hours, days, priorities and a date range. The timeline shows the whole week at a glance, and the screen resolves it exactly as the preview did.',
    src: '/shots/campaign.webp', label: 'paskall · Campaign', flip: true,
  },
  {
    eyebrow: 'Screens', title: 'Know every screen without walking to it.',
    text: 'Online or not, what it is playing and through which rule, dropped frames, download speed, the player version, and whether it is fully managed. Errors arrive with the screen they came from. A probe asks a screen to check in right now.',
    src: '/shots/screens.webp', label: 'paskall · Screens', flip: false,
  },
  {
    eyebrow: 'Playlists', title: 'Preview before you publish.',
    text: 'Every playlist plays back in a real-size preview of the screen it is for, portrait or landscape. Saving something that is already on air asks first, and names the screens it is about to change.',
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
            <p class="mt-4 leading-relaxed text-ink-muted">{{ s.text }}</p>
          </div>
          <div class="lg:col-span-8" :class="s.flip && 'lg:order-1'">
            <BrowserFrame :src="s.src" :alt="s.title" :label="s.label" />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
