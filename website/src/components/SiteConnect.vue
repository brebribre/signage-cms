<script setup lang="ts">
/** Connecting a screen: the pairing code a new player shows, which is all it takes. */
import FeatureCard from './FeatureCard.vue'
import { useI18n } from '@/i18n'

const { m } = useI18n()
</script>

<template>
  <section id="connect">
    <FeatureCard>
      <template #visual>
        <!-- The one stat, then the player's pairing screen under it, running off the card's
             corner. Nothing is laid over the picture, so a narrow card stays calm; on a wide
             page the screen takes the card's full width, cropped taller round the code, to
             fill the card beside its taller neighbour. -->
        <div class="relative">
          <div class="w-36 rounded-xl bg-sky-strong p-4 shadow-[0_20px_40px_-24px_rgba(0,24,77,0.5)] sm:w-40 sm:p-5">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-brand-deep/70">{{ m.connect.statUnder }}</p>
            <p class="display text-4xl text-brand-deep">{{ m.connect.statValue }}</p>
            <p class="mt-0.5 text-xs leading-snug text-brand-deep/80">{{ m.connect.statCaption }}</p>
          </div>
          <img
            src="/shots/player-pairing.webp" :alt="m.connect.photoAlt"
            class="ml-10 mt-5 block aspect-[1875/1032] w-[calc(100%-2.5rem)] rounded-tl-xl object-cover shadow-[0_30px_80px_-30px_rgba(0,24,77,0.45)] ring-1 ring-black/5 sm:ml-16 sm:w-[calc(100%-4rem)] lg:ml-0 lg:aspect-[4/3.4] lg:w-full"
            loading="lazy" decoding="async"
          />
        </div>
      </template>

      <h3 class="text-3xl leading-[1.1] sm:text-4xl">{{ m.connect.title }}</h3>
      <p class="mt-3 max-w-md leading-relaxed text-ink-muted">{{ m.connect.body }}</p>
    </FeatureCard>
  </section>
</template>
