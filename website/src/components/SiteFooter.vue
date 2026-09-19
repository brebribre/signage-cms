<script setup lang="ts">
import IconArrowForward from '~icons/material-symbols/arrow-forward'

import wordmark from '@/assets/paskall-wordmark.png'
const year = new Date().getFullYear()
</script>

<template>
  <section id="contact" class="mx-auto max-w-6xl px-5 pb-20 sm:px-8">
    <div class="reveal relative overflow-hidden rounded-3xl brand-gradient px-6 py-14 text-center text-ink-inverse sm:px-12 sm:py-20">
      <h2 class="text-3xl sm:text-5xl">Put your first screen on Paskall.</h2>
      <p class="mx-auto mt-4 max-w-xl text-white/80">Tell us how many screens and where they are. We set the account up, you type one code, and the wall is yours.</p>
      <a href="mailto:hello@paskall.com?subject=Paskall%20access" class="mt-8 inline-flex items-center gap-2 rounded-full bg-canvas px-5 py-3 text-sm text-brand transition-colors hover:bg-brand-soft">
        Request access <IconArrowForward class="size-4" />
      </a>
    </div>
  </section>
  <footer class="border-t border-line">
    <div class="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-8 text-[13px] text-ink-subtle sm:px-8">
      <img :src="wordmark" alt="Paskall" class="h-5 w-auto opacity-80" />
      <p>© {{ year }} Paskall. Digital signage that runs itself.</p>
      <a href="https://practical-benevolence-production-b7b2.up.railway.app" class="transition-colors hover:text-ink">Sign in to the CMS</a>
    </div>
  </footer>
</template>
