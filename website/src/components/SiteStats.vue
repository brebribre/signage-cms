<script setup lang="ts">
/** The numbers strip: the handful of facts that decide whether a screen stays on air. */
import IconBolt from '~icons/material-symbols/bolt'
import IconHd from '~icons/material-symbols/4k-outline'
import IconTimer from '~icons/material-symbols/timer-outline'
import IconWifiOff from '~icons/material-symbols/wifi-off'

const STATS = [
  { icon: IconTimer, value: '6 letters', label: 'To pair a new screen', tone: 'bg-tint text-brand' },
  { icon: IconBolt, value: '1 press', label: 'To update every screen', tone: 'bg-sky text-brand-bright' },
  { icon: IconHd, value: '4K', label: 'Video on Android boxes', tone: 'bg-sky text-brand-bright' },
  { icon: IconWifiOff, value: '0 gaps', label: 'When the internet drops', tone: 'bg-tint text-brand' },
]
</script>

<template>
  <section class="bg-gradient-to-b from-canvas via-brand-soft/60 to-canvas py-16 sm:py-20">
    <div class="mx-auto max-w-4xl px-5 text-center sm:px-8">
      <span class="reveal tag text-brand-deep">Proven</span>
      <h2 class="reveal mt-5 text-4xl leading-[1.1] sm:text-5xl">Built to keep playing</h2>
      <p class="reveal mt-6 inline-flex items-center gap-2 rounded-full bg-brand-deep px-4 py-1.5 text-xs text-white">
        <span class="size-1.5 rounded-full bg-accent" /> Files live on the screen, so the loop never waits on the network
      </p>

      <ul class="mx-auto mt-12 grid max-w-2xl gap-4 sm:grid-cols-2">
        <li
          v-for="s in STATS" :key="s.value"
          class="reveal flex items-center gap-4 rounded-3xl bg-white p-5 text-left shadow-[0_20px_50px_-32px_rgba(0,24,77,0.45)] ring-1 ring-line"
        >
          <span class="flex size-11 shrink-0 items-center justify-center rounded-2xl" :class="s.tone">
            <component :is="s.icon" class="size-5" aria-hidden="true" />
          </span>
          <span>
            <span class="display block text-3xl text-ink">{{ s.value }}</span>
            <span class="block text-sm text-ink-muted">{{ s.label }}</span>
          </span>
        </li>
      </ul>
    </div>
  </section>
</template>
