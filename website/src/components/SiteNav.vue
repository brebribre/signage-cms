<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import IconClose from '~icons/material-symbols/close'
import IconMenu from '~icons/material-symbols/menu'

import LocaleSwitch from './LocaleSwitch.vue'
import wordmark from '@/assets/paskall-wordmark.png'
import { useI18n } from '@/i18n'

const { m } = useI18n()
const LINKS = computed(() => [
  { href: '#connect', label: m.value.nav.links.screens },
  { href: '#design', label: m.value.nav.links.content },
  { href: '#publish', label: m.value.nav.links.publish },
  { href: '#platforms', label: m.value.nav.links.platforms },
  { href: '#faq', label: m.value.nav.links.faq },
])
const open = ref(false)
/** White on the blue hero at the top; ink on white, with a hairline and a little blur, once the
 *  page moves under it. */
const past = ref(false)
const onScroll = () => { past.value = window.scrollY > 12 }
/** Whether the bar is still over the hero, and so drawn in white. */
const onHero = computed(() => !past.value && !open.value)
onMounted(() => { onScroll(); window.addEventListener('scroll', onScroll, { passive: true }) })
onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
</script>

<template>
  <header
    class="fixed inset-x-0 top-0 z-50 transition-all duration-300"
    :class="onHero ? 'border-b border-transparent bg-transparent' : 'border-b border-line bg-canvas/90 backdrop-blur'"
  >
    <nav class="mx-auto flex max-w-7xl items-center justify-between px-5 py-4 sm:px-8" :aria-label="m.nav.label">
      <a href="#top" class="flex items-center">
        <img :src="wordmark" alt="Paskall" class="h-6 w-auto transition-all duration-300" :class="onHero && 'brightness-0 invert'" />
      </a>
      <ul class="hidden items-center gap-8 lg:flex">
        <li v-for="l in LINKS" :key="l.href">
          <a :href="l.href" class="text-sm transition-colors" :class="onHero ? 'text-white/85 hover:text-white' : 'text-ink hover:text-brand'">{{ l.label }}</a>
        </li>
      </ul>
      <div class="hidden items-center gap-5 lg:flex">
        <LocaleSwitch :inverse="onHero" />
        <a href="https://app.paskall.co.id" class="text-sm font-medium transition-colors" :class="onHero ? 'text-white hover:text-sky' : 'text-ink hover:text-brand'">{{ m.nav.signIn }}</a>
        <a
          href="#contact" class="rounded-full px-5 py-2.5 text-sm font-medium transition-colors"
          :class="onHero ? 'bg-white text-brand-deep hover:bg-sky' : 'bg-brand-deep text-white hover:bg-brand'"
        >{{ m.nav.requestAccess }}</a>
      </div>
      <div class="flex items-center gap-2 lg:hidden">
        <LocaleSwitch :inverse="onHero" />
        <button type="button" class="rounded-full p-2" :class="onHero ? 'text-white' : 'text-ink'" :aria-label="m.nav.menu" :aria-expanded="open" @click="open = !open">
          <component :is="open ? IconClose : IconMenu" class="size-6" />
        </button>
      </div>
    </nav>
    <div v-if="open" class="border-t border-line bg-canvas px-5 py-4 lg:hidden">
      <ul class="flex flex-col gap-3">
        <li v-for="l in LINKS" :key="l.href"><a :href="l.href" class="block text-base text-ink" @click="open = false">{{ l.label }}</a></li>
        <li><a href="https://app.paskall.co.id" class="block text-base text-ink">{{ m.nav.signIn }}</a></li>
        <li><a href="#contact" class="mt-2 inline-block rounded-full bg-brand-deep px-5 py-2.5 text-sm text-white" @click="open = false">{{ m.nav.requestAccess }}</a></li>
      </ul>
    </div>
  </header>
</template>
