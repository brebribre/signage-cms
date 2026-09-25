<script setup lang="ts">
/** Every screen, whatever it runs on, answering to one place. */
import { computed } from 'vue'

import FeatureCard from './FeatureCard.vue'
import { useI18n } from '@/i18n'

const PHOTOS = ['/shots/screen-lobby.webp', '/shots/screen-totem.webp', '/shots/screen-cafe.webp']
const { m } = useI18n()
const SCREENS = computed(() => m.value.connect.screens.map((s, i) => ({ ...s, src: PHOTOS[i] })))
</script>

<template>
  <section id="connect">
    <FeatureCard>
      <template #visual>
        <!-- A photo of a screen in its place, running off the card's corner, with the stat and
             the fleet laid over it. -->
        <div class="relative pt-10">
          <img
            src="/shots/screen-cafe.webp" :alt="m.connect.photoAlt"
            class="ml-10 block aspect-[4/4.6] w-[calc(100%-2.5rem)] sm:aspect-[4/3.1] rounded-tl-xl object-cover sm:ml-16 sm:w-[calc(100%-4rem)]" loading="lazy" decoding="async"
          />
          <div class="absolute top-0 left-0 w-36 rounded-xl bg-sky-strong p-4 shadow-[0_20px_40px_-24px_rgba(0,24,77,0.5)] sm:w-40 sm:p-5">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-brand-deep/70">{{ m.connect.statUnder }}</p>
            <p class="display text-4xl text-brand-deep">{{ m.connect.statValue }}</p>
            <p class="mt-0.5 text-xs leading-snug text-brand-deep/80">{{ m.connect.statCaption }}</p>
          </div>
          <ul class="absolute bottom-6 left-0 w-56 rounded-xl bg-white p-2 shadow-[0_24px_60px_-28px_rgba(0,24,77,0.5)] sm:bottom-8 sm:w-64">
            <li v-for="s in SCREENS" :key="s.src" class="flex items-center gap-3 rounded-lg p-1.5">
              <img :src="s.src" alt="" class="size-9 shrink-0 rounded-lg object-cover" loading="lazy" decoding="async" />
              <span class="min-w-0 flex-1">
                <span class="block truncate text-sm text-ink">{{ s.name }}</span>
                <span class="block text-[11px] text-ink-subtle">{{ s.kind }}</span>
              </span>
              <span class="flex items-center gap-1 text-[10px] uppercase tracking-wider text-emerald-600">
                <span class="size-1.5 rounded-full bg-emerald-500" /> {{ m.connect.live }}
              </span>
            </li>
          </ul>
        </div>
      </template>

      <h3 class="text-3xl leading-[1.1] sm:text-4xl">{{ m.connect.title }}</h3>
      <p class="mt-3 max-w-md leading-relaxed text-ink-muted">{{ m.connect.body }}</p>
    </FeatureCard>
  </section>
</template>
