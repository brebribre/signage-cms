<script setup lang="ts">
/**
 * The /software page, reached from the nav and the footer, in two sections. Marien CMS, the
 * control room screens are run from, on one wide card: the words beside the CMS itself. Then
 * Marien Player, what goes on the screens, as two equal cards: the Android app on a portrait
 * signage totem, and the web player in a smart TV's browser. Each card says what the piece is
 * for and links to where it opens or downloads.
 */
import { computed, watchEffect } from 'vue'
import IconAndroid from '~icons/material-symbols/android'
import IconArrow from '~icons/material-symbols/arrow-outward'
import IconLanguage from '~icons/material-symbols/language'

import { track } from '@/composables/useAnalytics'
import { useI18n } from '@/i18n'

const { m } = useI18n()
// After the i18n module's own title effect, so this page's title wins, in either language.
watchEffect(() => { document.title = m.value.software.metaTitle })

const cms = computed(() => m.value.software.items[0])
const android = computed(() => m.value.software.items[1])
const web = computed(() => m.value.software.items[2])
const STATEMENT = 'reveal max-w-4xl text-[2.125rem] leading-[1.1] sm:text-5xl lg:text-6xl lg:leading-[1.05]'
const GRADIENT = 'bg-gradient-to-r from-brand-strong to-brand-bright bg-clip-text text-transparent'
const LINK = 'mt-auto inline-flex items-center gap-1.5 self-start pt-5 text-sm font-medium text-brand transition-colors hover:text-brand-strong'
const CARD = 'flex flex-col overflow-hidden rounded-2xl bg-brand-soft ring-1 ring-tint-strong/60'
</script>

<template>
  <div class="mx-auto max-w-7xl px-5 pb-10 pt-28 sm:px-8 sm:pt-36">
    <!-- Marien CMS -->
    <section id="cms">
      <h1 :class="STATEMENT">{{ m.software.cms.lead }} <span :class="GRADIENT">{{ m.software.cms.rest }}</span></h1>

      <article class="reveal mt-10 grid overflow-hidden rounded-2xl bg-brand-soft ring-1 ring-tint-strong/60 sm:mt-14 lg:grid-cols-[0.8fr_1.2fr]">
        <div class="flex flex-col p-6 sm:p-8 lg:p-10">
          <h2 class="text-3xl leading-[1.1] sm:text-4xl">{{ cms.name }}</h2>
          <p class="mt-3 max-w-md leading-relaxed text-ink-muted">{{ cms.text }}</p>
          <a href="https://app.marien.co.id" target="_blank" rel="noopener" :class="LINK" @click="track('open_cms', { location: 'software' })">
            {{ cms.link }}<IconArrow class="size-4" aria-hidden="true" />
          </a>
        </div>
        <!-- The CMS in a browser window, running off the card's right and bottom edges. -->
        <div class="relative overflow-hidden pl-6 pt-2 sm:pl-8 lg:pt-10">
          <div class="card-sweep pointer-events-none absolute -right-[30%] -left-[10%] top-[10%] h-[90%] -rotate-[22deg] rounded-[50%]" aria-hidden="true" />
          <div class="relative -mb-2 -mr-2 overflow-hidden rounded-tl-xl bg-white shadow-[0_30px_60px_-30px_rgba(0,24,77,0.55)] ring-1 ring-line">
            <div class="flex items-center gap-1.5 border-b border-line bg-surface px-3 py-2">
              <span class="size-2 rounded-full bg-line-strong" /><span class="size-2 rounded-full bg-line-strong" /><span class="size-2 rounded-full bg-line-strong" />
              <span class="ml-2 truncate rounded bg-white px-2 py-0.5 text-[10px] text-ink-muted ring-1 ring-line">app.marien.co.id</span>
            </div>
            <img src="/shots/overview.webp" :alt="cms.alt" class="block aspect-[16/10] w-full object-cover object-left-top" loading="lazy" decoding="async" />
          </div>
        </div>
      </article>
    </section>

    <!-- Marien Player -->
    <section id="player" class="mt-20 sm:mt-28">
      <h2 :class="STATEMENT">{{ m.software.player.lead }} <span :class="GRADIENT">{{ m.software.player.rest }}</span></h2>

      <div class="reveal mt-10 grid gap-4 sm:mt-14 sm:gap-6 md:grid-cols-2">
        <!-- Android: a portrait signage totem, black like the hero's, whole on its stand. -->
        <article :class="CARD">
          <div class="relative flex aspect-[4/3] items-center justify-center overflow-hidden">
            <div class="card-sweep pointer-events-none absolute -right-[30%] -left-[10%] top-[20%] h-[90%] -rotate-[22deg] rounded-[50%]" aria-hidden="true" />
            <!-- Sized by height, at a real totem's shape: the screen, then a short stand. -->
            <div class="relative mt-[6%] flex aspect-[9/19] h-[84%] flex-col items-center">
              <div class="w-full rounded-t-[0.5rem] bg-gradient-to-b from-[#1b1e24] to-[#0f1115] p-1 shadow-[0_30px_60px_-30px_rgba(0,24,77,0.6),inset_0_1px_0_rgba(255,255,255,0.12)] ring-1 ring-black/60">
                <img src="/shots/hero/menu.webp" :alt="android.alt" class="block aspect-[9/15] w-full object-cover" loading="lazy" decoding="async" />
              </div>
              <div class="w-full flex-1 bg-gradient-to-b from-[#0f1115] via-[#1b1e24] to-[#14161b] ring-1 ring-black/60" aria-hidden="true" />
              <div class="h-1.5 w-[124%] rounded-sm bg-[#0b0d10] shadow-[0_14px_24px_-10px_rgba(0,24,77,0.55)]" aria-hidden="true" />
              <span class="absolute -right-5 -top-3 flex size-10 items-center justify-center rounded-full bg-white text-[#3ddc84] shadow-md ring-1 ring-line" aria-hidden="true">
                <IconAndroid class="size-6" />
              </span>
            </div>
          </div>
          <div class="flex flex-1 flex-col bg-white/70 p-6 sm:p-7">
            <h3 class="text-2xl leading-[1.15]">{{ android.name }}</h3>
            <p class="mt-2 leading-relaxed text-ink-muted">{{ android.text }}</p>
            <a href="https://api.marien.co.id/player/download" :class="LINK" @click="track('download_android', { location: 'software' })">
              {{ android.link }}<IconArrow class="size-4" aria-hidden="true" />
            </a>
          </div>
        </article>

        <!-- Web: the player in a smart TV's browser, its address showing. -->
        <article :class="CARD">
          <div class="relative flex aspect-[4/3] items-center justify-center overflow-hidden px-6 sm:px-8">
            <div class="card-sweep pointer-events-none absolute -right-[30%] -left-[10%] top-[20%] h-[90%] -rotate-[22deg] rounded-[50%]" aria-hidden="true" />
            <div class="relative w-full">
              <div class="overflow-hidden rounded-lg bg-[#0f1115] p-1.5 shadow-[0_30px_60px_-30px_rgba(0,24,77,0.6)]">
                <div class="flex items-center gap-1.5 rounded-t bg-[#1d2027] px-2 py-1">
                  <span class="truncate rounded bg-[#2a2e37] px-2 py-0.5 text-[10px] text-white/70">player.marien.co.id</span>
                </div>
                <img src="/shots/software/web-screen.webp" :alt="web.alt" class="block aspect-video w-full" loading="lazy" decoding="async" />
              </div>
              <div class="mx-auto h-2 w-1/4 rounded-b bg-[#0f1115]" aria-hidden="true" />
              <span class="absolute -right-2 -top-3 flex size-10 items-center justify-center rounded-full bg-white text-brand shadow-md ring-1 ring-line" aria-hidden="true">
                <IconLanguage class="size-6" />
              </span>
            </div>
          </div>
          <div class="flex flex-1 flex-col bg-white/70 p-6 sm:p-7">
            <h3 class="text-2xl leading-[1.15]">{{ web.name }}</h3>
            <p class="mt-2 leading-relaxed text-ink-muted">{{ web.text }}</p>
            <a href="https://player.marien.co.id" target="_blank" rel="noopener" :class="LINK" @click="track('open_web_player', { location: 'software' })">
              {{ web.link }}<IconArrow class="size-4" aria-hidden="true" />
            </a>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>
