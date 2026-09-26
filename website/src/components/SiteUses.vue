<script setup lang="ts">
/**
 * What people run Marien for: advertising, information and interactive media, each as a photo
 * of a screen in a busy place with Marien content on it, and the words under it. Three across on
 * a wide page; on a phone a row that swipes, the next card
 * peeking in so it reads as more to see.
 *
 * The photos are generated stock scenes with the screens keyed in afterwards: the Nusantara
 * café promotion, a station's departures board, and a mall directory website under a finger.
 */
import { useI18n } from '@/i18n'

const { m } = useI18n()
const PHOTOS = ['/shots/uses/advertising.webp', '/shots/uses/information.webp', '/shots/uses/interactive.webp']
</script>

<template>
  <section id="uses" class="mt-10 sm:mt-14">
    <p class="reveal text-xs font-semibold uppercase tracking-wider text-ink-subtle">{{ m.uses.label }}</p>
    <ul
      class="reveal -mx-5 mt-4 flex snap-x snap-mandatory scroll-pl-5 gap-4 overflow-x-auto px-5 pb-2 [scrollbar-width:none] sm:mx-0 sm:grid sm:snap-none sm:grid-cols-3 sm:gap-6 sm:overflow-visible sm:px-0 sm:pb-0 [&::-webkit-scrollbar]:hidden"
    >
      <li v-for="(u, i) in m.uses.items" :key="u.tag" class="group w-[82%] shrink-0 snap-start sm:w-auto">
        <!-- The photo whole, nothing over it: the screen in it is the point. -->
        <div class="aspect-[4/5] overflow-hidden rounded-2xl bg-tint ring-1 ring-tint-strong/60">
          <img
            :src="PHOTOS[i]" :alt="u.alt"
            class="size-full object-cover transition-transform duration-700 ease-out group-hover:scale-[1.03]"
            loading="lazy" decoding="async"
          />
        </div>
        <span class="mt-5 inline-flex items-center gap-2 rounded-full bg-brand-soft px-3 py-1 text-xs font-medium text-brand">
          <span class="size-1.5 rounded-full bg-brand" />{{ u.tag }}
        </span>
        <h3 class="mt-3 text-2xl leading-[1.15]">{{ u.title }}</h3>
        <p class="mt-2 max-w-sm leading-relaxed text-ink-muted">{{ u.body }}</p>
      </li>
    </ul>
  </section>
</template>
