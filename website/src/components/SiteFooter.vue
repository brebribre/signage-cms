<script setup lang="ts">
import IconArrowForward from '~icons/material-symbols/arrow-forward'

import wordmark from '@/assets/paskall-wordmark.png'
const year = new Date().getFullYear()
</script>

<template>
  <!-- The closing band takes the same diagonal as the players section, so the page ends the
       way it began. -->
  <section id="contact" class="angled-band angled-band-up relative mt-10 text-ink-inverse">
    <div class="relative mx-auto max-w-7xl px-5 pt-[calc(7vw+4rem)] pb-20 text-center sm:px-8 sm:pb-24">
      <h2 class="reveal text-3xl sm:text-5xl">Put your first screen on Paskall.</h2>
      <p class="reveal mx-auto mt-4 max-w-xl text-white/80">
        Tell us how many screens and where they are. We set the account up, you type one code, and the wall is yours.
      </p>
      <a
        href="mailto:hello@paskall.com?subject=Paskall%20access"
        class="reveal mt-8 inline-flex items-center gap-2 rounded-full bg-white px-5 py-3 text-sm text-brand transition-colors hover:bg-white/90"
      >
        Request access <IconArrowForward class="size-4" />
      </a>
    </div>
  </section>
  <footer class="bg-brand-deep text-white/60">
    <div class="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-5 py-8 text-[13px] sm:px-8">
      <img :src="wordmark" alt="Paskall" class="h-5 w-auto brightness-0 invert opacity-70" />
      <p>© {{ year }} Paskall. Digital signage that runs itself.</p>
      <a href="https://practical-benevolence-production-b7b2.up.railway.app" class="transition-colors hover:text-white">Sign in to the CMS</a>
    </div>
  </footer>
</template>
