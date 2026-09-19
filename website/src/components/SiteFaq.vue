<script setup lang="ts">
import { ref } from 'vue'
import IconExpand from '~icons/material-symbols/expand-more'

const QA = [
  { q: 'What hardware do I need?', a: 'Any Android TV box or tablet, or a smart TV with a browser. Full remote control needs the Android player set up as Device Owner, which we can do for you.' },
  { q: 'What happens when the internet drops?', a: 'Nothing visible. Files live on the screen, so the loop keeps playing and catches up when the network returns.' },
  { q: 'Can staff change content safely?', a: 'Yes. They get the screens you grant, and anything that would change a screen waits for your approval.' },
  { q: 'How big can a video be?', a: 'Upload the original. Paskall makes a copy every screen can play, 4K for Android boxes and 1080p for TV browsers.' },
]
const open = ref<number | null>(0)
</script>

<template>
  <section id="faq" class="bg-page py-20 sm:py-28">
    <div class="mx-auto max-w-3xl px-5 sm:px-8">
      <h2 class="reveal text-3xl sm:text-4xl">Questions people ask first.</h2>
      <ul class="mt-8 divide-y divide-line border-y border-line">
        <li v-for="(item, i) in QA" :key="item.q" class="reveal">
          <button type="button" class="flex w-full items-center justify-between gap-4 py-5 text-left" :aria-expanded="open === i" @click="open = open === i ? null : i">
            <span class="text-base text-ink">{{ item.q }}</span>
            <IconExpand class="size-5 shrink-0 text-ink-subtle transition-transform" :class="open === i && 'rotate-180'" />
          </button>
          <p v-if="open === i" class="pb-5 text-sm leading-relaxed text-ink-muted">{{ item.a }}</p>
        </li>
      </ul>
    </div>
  </section>
</template>
