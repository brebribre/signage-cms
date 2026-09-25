<script setup lang="ts">
/** Every screen, whatever it runs on, answering to one place. */
import IconArrowForward from '~icons/material-symbols/arrow-forward'

import FeatureCard from './FeatureCard.vue'

const SCREENS = [
  { src: '/shots/screen-lobby.webp', name: 'Lobby TV', kind: 'Android box' },
  { src: '/shots/screen-totem.webp', name: 'Entrance totem', kind: 'Smart TV' },
  { src: '/shots/screen-cafe.webp', name: 'Cafe screen', kind: 'Browser' },
]
</script>

<template>
  <section id="connect">
    <FeatureCard tone="tint" tag="Screens">
      <template #visual>
        <!-- A photo of a screen in its place, with the stat and the fleet laid over it. -->
        <div class="relative pt-8 pl-8 pb-10 sm:pt-10 sm:pl-14">
          <img
            src="/shots/screen-cafe.webp" alt="A cafe screen run by Paskall"
            class="aspect-[4/3.4] w-full rounded-3xl object-cover" loading="lazy" decoding="async"
          />
          <div class="absolute top-0 left-0 w-36 rounded-3xl bg-sky-strong p-4 sm:w-40 sm:p-5">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-brand-deep/70">Under</p>
            <p class="display text-4xl text-brand-deep">1 min</p>
            <p class="mt-0.5 text-xs leading-snug text-brand-deep/80">To connect a new screen</p>
          </div>
          <ul class="absolute right-3 bottom-0 w-56 rounded-3xl bg-white p-2 shadow-[0_24px_60px_-28px_rgba(0,24,77,0.5)] sm:right-6 sm:w-64">
            <li v-for="s in SCREENS" :key="s.name" class="flex items-center gap-3 rounded-2xl p-1.5">
              <img :src="s.src" alt="" class="size-9 shrink-0 rounded-xl object-cover" loading="lazy" decoding="async" />
              <span class="min-w-0 flex-1">
                <span class="block truncate text-sm text-ink">{{ s.name }}</span>
                <span class="block text-[11px] text-ink-subtle">{{ s.kind }}</span>
              </span>
              <span class="flex items-center gap-1 text-[10px] uppercase tracking-wider text-emerald-600">
                <span class="size-1.5 rounded-full bg-emerald-500" /> Live
              </span>
            </li>
          </ul>
        </div>
      </template>

      <h2 class="mt-5 text-4xl leading-[1.1] sm:text-5xl">Connect your screens</h2>
      <p class="mt-5 max-w-md leading-relaxed text-ink-muted">
        One code, any screen. The player shows six letters; type them into the dashboard and the
        screen joins your fleet. Android boxes, smart TVs and browsers sit side by side.
      </p>
      <a href="#contact" class="mt-8 inline-flex items-center gap-2 rounded-full bg-brand-deep px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-brand">
        Request access <IconArrowForward class="size-4" />
      </a>
    </FeatureCard>
  </section>
</template>
