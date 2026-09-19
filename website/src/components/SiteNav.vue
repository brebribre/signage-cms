<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import IconClose from '~icons/material-symbols/close'
import IconMenu from '~icons/material-symbols/menu'

import logo from '@/assets/paskall-logo.png'

const LINKS = [
  { href: '#product', label: 'Product' },
  { href: '#how', label: 'How it works' },
  { href: '#players', label: 'Players' },
  { href: '#plans', label: 'Plans' },
]
const open = ref(false)
const scrolled = ref(false)
const onScroll = () => { scrolled.value = window.scrollY > 8 }
onMounted(() => { onScroll(); window.addEventListener('scroll', onScroll, { passive: true }) })
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <header
    class="sticky top-0 z-50 transition-colors duration-300"
    :class="scrolled ? 'border-b border-line bg-canvas/85 backdrop-blur' : 'bg-transparent'"
  >
    <nav class="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8" aria-label="Site">
      <a href="#top" class="flex items-center gap-2">
        <img :src="logo" alt="Paskall" class="h-7 w-auto" />
      </a>
      <ul class="hidden items-center gap-8 md:flex">
        <li v-for="l in LINKS" :key="l.href">
          <a :href="l.href" class="text-sm text-ink-muted transition-colors hover:text-ink">{{ l.label }}</a>
        </li>
      </ul>
      <div class="hidden items-center gap-3 md:flex">
        <a href="https://practical-benevolence-production-b7b2.up.railway.app" class="text-sm text-ink-muted transition-colors hover:text-ink">Sign in</a>
        <a href="#contact" class="rounded-full bg-brand px-4 py-2 text-sm text-ink-inverse transition-colors hover:bg-hover">Request access</a>
      </div>
      <button type="button" class="rounded-full p-2 text-ink md:hidden" aria-label="Menu" @click="open = !open">
        <component :is="open ? IconClose : IconMenu" class="size-6" />
      </button>
    </nav>
    <div v-if="open" class="border-t border-line bg-canvas px-5 py-4 md:hidden">
      <ul class="flex flex-col gap-3">
        <li v-for="l in LINKS" :key="l.href"><a :href="l.href" class="block text-base text-ink" @click="open = false">{{ l.label }}</a></li>
        <li><a href="#contact" class="mt-2 inline-block rounded-full bg-brand px-4 py-2 text-sm text-ink-inverse" @click="open = false">Request access</a></li>
      </ul>
    </div>
  </header>
</template>
