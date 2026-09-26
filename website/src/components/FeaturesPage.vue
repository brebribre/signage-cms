<script setup lang="ts">
/**
 * The /features page, reached from the nav and from the home page's editor card: every feature on
 * a card of its own, in the same style as that card (the title and a line at the top, a real
 * screenshot in a browser frame running off the corner). The first three are the editor card's
 * steps, in the same words; the rest are what an owner does with a team.
 */
import { computed, watchEffect } from 'vue'

import BrowserFrame from './BrowserFrame.vue'
import FeatureCard from './FeatureCard.vue'
import { useI18n } from '@/i18n'

/** The shots and their window titles are the CMS's own, in English; the words are the page's. */
const SHOTS = [
  { chrome: 'marien · Scene', src: '/shots/scene.webp' },
  { chrome: 'marien · Playlist', src: '/shots/playlist.webp' },
  { chrome: 'marien · Campaign', src: '/shots/campaign.webp' },
  { chrome: 'marien · User management', src: '/shots/users.webp' },
  { chrome: 'marien · Reviews', src: '/shots/reviews.webp' },
]
const { m } = useI18n()
const CARDS = computed(() =>
  [...m.value.design.tabs, ...m.value.featuresPage.more].map((f, i) => ({ ...f, ...SHOTS[i] })),
)
// Runs after the i18n module's own title effect, so this page's title wins, in either language.
watchEffect(() => { document.title = m.value.featuresPage.metaTitle })
</script>

<template>
  <section id="features" class="mx-auto max-w-7xl px-5 pb-10 pt-28 sm:px-8 sm:pt-36">
    <h1 class="reveal max-w-4xl text-[2.125rem] leading-[1.1] sm:text-5xl lg:text-6xl lg:leading-[1.05]">
      {{ m.featuresPage.lead }} <span class="text-ink-muted">{{ m.featuresPage.rest }}</span>
    </h1>

    <!-- The first card across the whole row, then two to a row. -->
    <div class="mt-10 grid grid-cols-1 gap-4 sm:mt-14 sm:gap-6 lg:grid-cols-2">
      <FeatureCard v-for="(c, i) in CARDS" :key="c.src" class="reveal" :class="i === 0 && 'lg:col-span-2'">
        <h2 class="text-3xl leading-[1.1] sm:text-4xl">{{ c.title }}</h2>
        <p class="mt-3 max-w-md leading-relaxed text-ink-muted">{{ c.text }}</p>

        <template #visual>
          <BrowserFrame :label="c.chrome" class="rounded-tl-xl border-r-0 border-b-0">
            <div class="relative w-full bg-page" :class="i === 0 ? 'aspect-[16/7]' : 'aspect-[16/10]'">
              <img
                :src="c.src" :alt="`${c.label} ${m.design.inMarien}`"
                class="absolute inset-0 size-full object-cover object-left-top"
                loading="lazy" decoding="async"
              />
            </div>
          </BrowserFrame>
        </template>
      </FeatureCard>
    </div>
  </section>
</template>
