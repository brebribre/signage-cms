<script setup lang="ts">
import { ref } from 'vue'
import IconAdd from '~icons/material-symbols/add'

const QA = [
  { q: 'What hardware do I need?', a: 'Any Android TV box or tablet, or a smart TV with a browser. Full remote control needs the Android player set up as Device Owner, which we can do for you.' },
  { q: 'What happens when the internet drops?', a: 'Nothing visible. Files live on the screen, so the loop keeps playing and catches up when the network returns.' },
  { q: 'Can staff change content safely?', a: 'Yes. They get the screens you grant, and anything that would change a screen waits for your approval.' },
  { q: 'How big can a video be?', a: 'Upload the original. Paskall makes a copy every screen can play, 4K for Android boxes and 1080p for TV browsers.' },
]
const open = ref<number | null>(0)
</script>

<template>
  <section id="faq" class="mx-auto max-w-7xl px-5 py-20 sm:px-8 sm:py-28">
    <div class="grid gap-10 lg:grid-cols-12">
      <div class="reveal lg:col-span-5">
        <span class="tag text-brand-deep">FAQ</span>
        <h2 class="mt-5 text-4xl leading-[1.1] sm:text-5xl">Questions people ask first</h2>
        <p class="mt-5 text-ink-muted">Something else? <a href="mailto:hello@paskall.com" class="text-brand underline underline-offset-4">Write to us</a>.</p>
      </div>
      <ul class="reveal flex flex-col gap-3 lg:col-span-7">
        <li v-for="(item, i) in QA" :key="item.q" class="rounded-3xl transition-colors" :class="open === i ? 'bg-tint' : 'bg-surface ring-1 ring-line'">
          <button type="button" class="flex w-full items-center justify-between gap-4 px-6 py-5 text-left" :aria-expanded="open === i" @click="open = open === i ? null : i">
            <span class="display text-lg text-ink">{{ item.q }}</span>
            <span class="flex size-8 shrink-0 items-center justify-center rounded-full transition-colors" :class="open === i ? 'bg-brand-deep text-white' : 'bg-white text-ink ring-1 ring-line'">
              <IconAdd class="size-5 transition-transform" :class="open === i && 'rotate-45'" />
            </span>
          </button>
          <p v-if="open === i" class="px-6 pb-6 text-sm leading-relaxed text-ink-muted">{{ item.a }}</p>
        </li>
      </ul>
    </div>
  </section>
</template>
