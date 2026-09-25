<script setup lang="ts">
import IconArrowForward from '~icons/material-symbols/arrow-forward'

import wordmark from '@/assets/paskall-wordmark.png'
const year = new Date().getFullYear()
const LINKS = [
  { href: '#connect', label: 'Screens' },
  { href: '#design', label: 'Content' },
  { href: '#publish', label: 'Publish' },
  { href: '#plans', label: 'Pricing' },
  { href: '#faq', label: 'FAQ' },
]
</script>

<template>
  <!-- The closing card: the same pastel rounded shape as the features, with the ask in it. -->
  <section id="contact" class="mx-auto max-w-7xl px-5 pb-10 sm:px-8">
    <div class="reveal relative overflow-hidden rounded-[2rem] bg-sky px-6 py-16 text-center sm:rounded-[2.5rem] sm:py-24">
      <div class="hero-ring pointer-events-none absolute -bottom-48 left-1/2 h-96 w-[48rem] -translate-x-1/2 rounded-full" aria-hidden="true" />
      <div class="hero-ring pointer-events-none absolute -bottom-72 left-1/2 h-[36rem] w-[64rem] -translate-x-1/2 rounded-full" aria-hidden="true" />
      <span class="tag relative text-brand-deep">Get started</span>
      <h2 class="relative mx-auto mt-5 max-w-2xl text-4xl leading-[1.1] sm:text-6xl">Put your first screen on Paskall</h2>
      <p class="relative mx-auto mt-5 max-w-xl text-lg text-ink-muted">
        Tell us how many screens. We set the account up, you type one code.
      </p>
      <div class="relative mt-9 flex flex-wrap justify-center gap-3">
        <a
          href="mailto:hello@paskall.com?subject=Paskall%20access"
          class="inline-flex items-center gap-2 rounded-full bg-brand-deep px-6 py-3.5 text-sm font-medium text-white transition-colors hover:bg-brand"
        >
          Request access <IconArrowForward class="size-4" />
        </a>
        <a href="https://app.paskall.co.id" class="rounded-full border border-ink/80 px-6 py-3.5 text-sm font-medium text-ink transition-colors hover:bg-ink hover:text-white">
          Sign in
        </a>
      </div>
    </div>
  </section>
  <footer class="border-t border-line">
    <div class="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-10 text-sm sm:px-8 md:flex-row md:items-center md:justify-between">
      <img :src="wordmark" alt="Paskall" class="h-5 w-auto self-start md:self-auto" />
      <ul class="flex flex-wrap gap-x-6 gap-y-2 text-ink-muted">
        <li v-for="l in LINKS" :key="l.href"><a :href="l.href" class="transition-colors hover:text-ink">{{ l.label }}</a></li>
      </ul>
      <p class="text-ink-subtle">© {{ year }} Paskall</p>
    </div>
  </footer>
</template>
