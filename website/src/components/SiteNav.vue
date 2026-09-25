<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import IconClose from '~icons/material-symbols/close'
import IconMenu from '~icons/material-symbols/menu'

import LocaleSwitch from './LocaleSwitch.vue'
import wordmark from '@/assets/paskall-wordmark.png'
import { homeSection } from '@/composables/usePage'
import { useI18n } from '@/i18n'

const { m } = useI18n()
/** Only links that open another page. The home page's sections are reached by scrolling, and
 *  the footer still lists them. */
const LINKS = computed(() => [
  { href: '/demo', label: m.value.nav.links.demo },
  { href: 'https://app.paskall.co.id', label: m.value.nav.signIn },
])
const open = ref(false)
/** Clear over the hero at the top; white, with a hairline and a little blur, once the page
 *  moves under it. */
const past = ref(false)
const onScroll = () => { past.value = window.scrollY > 12 }
/** Whether the bar is still over the top of the hero, and so drawn without a background. */
const onHero = computed(() => !past.value && !open.value)
onMounted(() => { onScroll(); window.addEventListener('scroll', onScroll, { passive: true }) })
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
// The phone menu covers the whole screen, so the page behind it stays put while it's open.
watch(open, (v) => { document.documentElement.style.overflow = v ? 'hidden' : '' })
onBeforeUnmount(() => { document.documentElement.style.overflow = '' })
</script>

<template>
  <header
    class="fixed inset-x-0 top-0 z-50 transition-all duration-300"
    :class="
      open ? 'flex h-dvh flex-col border-b border-line bg-canvas lg:h-auto'
      : onHero ? 'border-b border-transparent bg-transparent' : 'border-b border-line bg-canvas/90 backdrop-blur'
    "
  >
    <nav class="mx-auto flex w-full max-w-7xl items-center justify-between px-5 py-4 sm:px-8" :aria-label="m.nav.label">
      <a :href="homeSection('top')" class="flex items-center">
        <img :src="wordmark" alt="Paskall" class="h-6 w-auto transition-all duration-300"  />
      </a>
      <div class="hidden items-center gap-6 lg:flex">
        <LocaleSwitch />
        <a v-for="l in LINKS" :key="l.href" :href="l.href" class="text-sm font-medium text-ink transition-colors hover:text-brand">{{ l.label }}</a>
        <a
          href="#contact" class="rounded-full bg-brand-deep px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand"
        >{{ m.nav.requestAccess }}</a>
      </div>
      <div class="flex items-center gap-2 lg:hidden">
        <LocaleSwitch />
        <button type="button" class="rounded-full bg-white/80 p-2 text-ink backdrop-blur" :aria-label="m.nav.menu" :aria-expanded="open" @click="open = !open">
          <component :is="open ? IconClose : IconMenu" class="size-6" />
        </button>
      </div>
    </nav>
    <!-- On a phone the menu takes the whole screen under the bar: the links large, the ask at
         the foot where a thumb reaches it. -->
    <div v-if="open" class="flex flex-1 flex-col overflow-y-auto border-t border-line px-5 pb-10 pt-8 lg:hidden">
      <ul class="flex flex-col gap-6">
        <li v-for="l in LINKS" :key="l.href">
          <a :href="l.href" class="display block text-3xl text-ink" @click="open = false">{{ l.label }}</a>
        </li>
      </ul>
      <a
        href="#contact" class="mt-auto block rounded-full bg-brand-deep px-6 py-4 text-center text-base font-medium text-white"
        @click="open = false"
      >{{ m.nav.requestAccess }}</a>
    </div>
  </header>
</template>
