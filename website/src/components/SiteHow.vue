<script setup lang="ts">
/** The three steps, as three cards with the part of the product each one happens in. */
import IconArrowForward from '~icons/material-symbols/arrow-forward'

const STEPS = [
  { n: '01', time: 'Under a minute', src: '/shots/screens.webp', title: 'Connect a screen', text: 'The player shows a six letter code. Type it in and the screen is yours.' },
  { n: '02', time: 'A few minutes', src: '/shots/playlist.webp', title: 'Build a playlist', text: 'Upload, arrange, add a headline. Preview at the screen’s real shape.' },
  { n: '03', time: 'One press', src: '/shots/campaign.webp', title: 'Deploy a campaign', text: 'Pick screens, pick content, deploy. They run themselves from there.' },
]
</script>

<template>
  <section id="how" class="mx-auto max-w-7xl px-5 pt-20 pb-4 sm:px-8 sm:pt-28">
    <div class="reveal text-center">
      <span class="tag text-brand-deep">How it works</span>
      <h2 class="mt-5 text-4xl leading-[1.1] sm:text-5xl">Up and playing in three steps</h2>
    </div>
    <ol class="mt-14 grid gap-6 md:grid-cols-3">
      <li v-for="s in STEPS" :key="s.n" class="reveal group flex flex-col">
        <div class="aspect-[1.6] overflow-hidden rounded-3xl bg-tint ring-1 ring-line">
          <img
            :src="s.src" :alt="s.title"
            class="size-full object-cover object-left-top transition-transform duration-500 group-hover:scale-[1.03]"
            loading="lazy" decoding="async"
          />
        </div>
        <p class="mt-5 text-[11px] font-medium uppercase tracking-wider text-ink-subtle">Step {{ s.n }} · {{ s.time }}</p>
        <h3 class="mt-2 text-xl">{{ s.title }}</h3>
        <p class="mt-1.5 text-sm leading-relaxed text-ink-muted">{{ s.text }}</p>
        <a href="#contact" class="mt-4 flex items-center justify-between border-t border-line pt-4 text-sm font-medium text-ink transition-colors hover:text-brand">
          Get started <IconArrowForward class="size-4" />
        </a>
      </li>
    </ol>
  </section>
</template>
