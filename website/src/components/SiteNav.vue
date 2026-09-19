<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import IconClose from '~icons/material-symbols/close'
import IconMenu from '~icons/material-symbols/menu'

import wordmark from '@/assets/paskall-wordmark.png'

const LINKS = [
  { href: '#connect', label: 'Connect' },
  { href: '#design', label: 'Design' },
  { href: '#publish', label: 'Publish' },
  { href: '#plans', label: 'Plans' },
]
const open = ref(false)
/** The nav sits on the gradient at the top, so it is white-on-colour until the page scrolls
 *  past the band, and ink-on-white after. */
const past = ref(false)
const onScroll = () => { past.value = window.scrollY > 24 }
onMounted(() => { onScroll(); window.addEventListener('scroll', onScroll, { passive: true }) })
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <header
    class="fixed inset-x-0 top-0 z-50 transition-all duration-300"
    :class="past ? 'border-b border-line bg-canvas/90 backdrop-blur' : 'border-b border-transparent'"
  >
    <nav class="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8" aria-label="Site">
      <a href="#top" class="flex items-center gap-2">
        <img :src="wordmark" alt="Paskall" class="h-6 w-auto transition-all duration-300" :class="!past && 'brightness-0 invert'" />
      </a>
      <ul class="hidden items-center gap-8 md:flex">
        <li v-for="l in LINKS" :key="l.href">
          <a
            :href="l.href"
            class="text-sm transition-colors"
            :class="past ? 'text-ink-muted hover:text-ink' : 'text-white/80 hover:text-white'"
          >{{ l.label }}</a>
        </li>
      </ul>
      <div class="hidden items-center gap-4 md:flex">
        <a
          href="https://practical-benevolence-production-b7b2.up.railway.app"
          class="text-sm transition-colors"
          :class="past ? 'text-ink-muted hover:text-ink' : 'text-white/80 hover:text-white'"
        >Sign in</a>
        <a
          href="#contact"
          class="rounded-full px-4 py-2 text-sm transition-colors"
          :class="past ? 'bg-brand text-ink-inverse hover:bg-hover' : 'bg-white text-brand hover:bg-white/90'"
        >Request access</a>
      </div>
      <button
        type="button" class="rounded-full p-2 md:hidden" :class="past ? 'text-ink' : 'text-white'"
        aria-label="Menu" @click="open = !open"
      >
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
