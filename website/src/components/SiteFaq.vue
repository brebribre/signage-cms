<script setup lang="ts">
import { ref } from 'vue'
import IconExpand from '~icons/material-symbols/expand-more'

const QA = [
  { q: 'What hardware do I need?', a: 'Any Android TV box or tablet for the Android player, or a smart TV with a browser. For full remote control — power schedules, silent updates, a locked kiosk — the Android player is set up as Device Owner, which we can do for you or ship pre-provisioned.' },
  { q: 'What happens when the internet drops?', a: 'Nothing visible. Every file is stored on the screen and the loop keeps playing. Downloads that were interrupted resume where they stopped, and the screen catches up on changes when the network returns.' },
  { q: 'Can my staff change content without breaking things?', a: 'Yes. A manager gets the screens you grant and the shared library. Anything they save that would change a screen goes to you as a review with a Before and After preview, and nothing reaches a screen until you approve it.' },
  { q: 'How big can a video be?', a: 'Upload the original. Paskall makes a copy every screen can play — kept at 4K for Android boxes, 1080p for TV browsers — so a phone video and a 4K render both just play.' },
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
