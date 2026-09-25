<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import IconClose from '~icons/material-symbols/close'
import IconMenu from '~icons/material-symbols/menu'

import wordmark from '@/assets/paskall-wordmark.png'

const LINKS = [
  { href: '#connect', label: 'Screens' },
  { href: '#design', label: 'Content' },
  { href: '#publish', label: 'Publish' },
  { href: '#platforms', label: 'Platforms' },
  { href: '#faq', label: 'FAQ' },
]
const open = ref(false)
/** White on white at the top; a hairline and a little blur once the page moves under it. */
const past = ref(false)
const onScroll = () => { past.value = window.scrollY > 12 }
onMounted(() => { onScroll(); window.addEventListener('scroll', onScroll, { passive: true }) })
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <header
    class="fixed inset-x-0 top-0 z-50 transition-all duration-300"
    :class="past || open ? 'border-b border-line bg-canvas/90 backdrop-blur' : 'border-b border-transparent bg-transparent'"
  >
    <nav class="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8" aria-label="Site">
      <a href="#top" class="flex items-center">
        <img :src="wordmark" alt="Paskall" class="h-6 w-auto" />
      </a>
      <ul class="hidden items-center gap-8 md:flex">
        <li v-for="l in LINKS" :key="l.href">
          <a :href="l.href" class="text-sm text-ink transition-colors hover:text-brand">{{ l.label }}</a>
        </li>
      </ul>
      <div class="hidden items-center gap-5 md:flex">
        <a href="https://app.paskall.co.id" class="text-sm font-medium text-ink transition-colors hover:text-brand">Sign in</a>
        <a href="#contact" class="rounded-full bg-brand-deep px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand">Request access</a>
      </div>
      <button type="button" class="rounded-full p-2 text-ink md:hidden" aria-label="Menu" :aria-expanded="open" @click="open = !open">
        <component :is="open ? IconClose : IconMenu" class="size-6" />
      </button>
    </nav>
    <div v-if="open" class="border-t border-line bg-canvas px-5 py-4 md:hidden">
      <ul class="flex flex-col gap-3">
        <li v-for="l in LINKS" :key="l.href"><a :href="l.href" class="block text-base text-ink" @click="open = false">{{ l.label }}</a></li>
        <li><a href="https://app.paskall.co.id" class="block text-base text-ink">Sign in</a></li>
        <li><a href="#contact" class="mt-2 inline-block rounded-full bg-brand-deep px-5 py-2.5 text-sm text-white" @click="open = false">Request access</a></li>
      </ul>
    </div>
  </header>
</template>
