<script setup lang="ts">
/**
 * The /software page, reached from the nav and the footer: the three pieces of Marien side by
 * side. The CMS, where screens are run from, and the two players that put a screen in touch with
 * it, the Android app and the web player. Each card shows the thing itself on the pale brand tint
 * the feature cards use, then its name, what it is for, and the link that opens or downloads it.
 */
import IconAndroid from '~icons/material-symbols/android'
import IconArrow from '~icons/material-symbols/arrow-outward'
import IconLanguage from '~icons/material-symbols/language'

import { track } from '@/composables/useAnalytics'
import { useI18n } from '@/i18n'
import { watchEffect } from 'vue'

const { m } = useI18n()
// After the i18n module's own title effect, so this page's title wins, in either language.
watchEffect(() => { document.title = m.value.software.metaTitle })
const LINKS = [
  { href: 'https://app.marien.co.id', event: 'open_cms' },
  { href: 'https://api.marien.co.id/player/download', event: 'download_android' },
  { href: 'https://player.marien.co.id', event: 'open_web_player' },
]
</script>

<template>
  <section id="software" class="mx-auto max-w-7xl px-5 pb-10 pt-28 sm:px-8 sm:pt-36">
    <h1 class="reveal max-w-4xl text-[2.125rem] leading-[1.1] sm:text-5xl lg:text-6xl lg:leading-[1.05]">
      {{ m.software.lead }} <span class="bg-gradient-to-r from-brand-strong to-brand-bright bg-clip-text text-transparent">{{ m.software.rest }}</span>
    </h1>

    <ul class="reveal mt-10 grid gap-4 sm:mt-14 sm:gap-6 lg:grid-cols-3">
      <li v-for="(s, i) in m.software.items" :key="s.name" class="flex flex-col overflow-hidden rounded-2xl bg-brand-soft ring-1 ring-tint-strong/60">
        <!-- The picture: the thing itself, on the card's sweep. -->
        <div class="relative flex aspect-[16/10] items-center justify-center overflow-hidden px-6 pt-8 sm:px-8">
          <div class="card-sweep pointer-events-none absolute -right-[30%] -left-[10%] top-[20%] h-[90%] -rotate-[22deg] rounded-[50%]" aria-hidden="true" />

          <!-- The CMS: a browser window with the overview in it. -->
          <div v-if="i === 0" class="relative w-full overflow-hidden rounded-t-xl bg-white shadow-[0_30px_60px_-30px_rgba(0,24,77,0.55)] ring-1 ring-line">
            <div class="flex items-center gap-1.5 border-b border-line bg-surface px-3 py-2">
              <span class="size-2 rounded-full bg-line-strong" /><span class="size-2 rounded-full bg-line-strong" /><span class="size-2 rounded-full bg-line-strong" />
              <span class="ml-2 truncate rounded bg-white px-2 py-0.5 text-[10px] text-ink-muted ring-1 ring-line">app.marien.co.id</span>
            </div>
            <img src="/shots/overview.webp" :alt="s.alt" class="block aspect-[16/10] w-full object-cover object-left-top" loading="lazy" decoding="async" />
          </div>

          <!-- The Android player: a screen in a black bezel, with the Android mark. -->
          <div v-else-if="i === 1" class="relative w-[92%]">
            <div class="rounded-lg bg-[#0f1115] p-1.5 shadow-[0_30px_60px_-30px_rgba(0,24,77,0.6)]">
              <img src="/shots/software/android-screen.webp" :alt="s.alt" class="block aspect-video w-full rounded" loading="lazy" decoding="async" />
            </div>
            <div class="mx-auto h-2 w-1/4 rounded-b bg-[#0f1115]" aria-hidden="true" />
            <span class="absolute -right-2 -top-3 flex size-10 items-center justify-center rounded-full bg-white text-[#3ddc84] shadow-md ring-1 ring-line" aria-hidden="true">
              <IconAndroid class="size-6" />
            </span>
          </div>

          <!-- The web player: a browser on the TV, its address showing. -->
          <div v-else class="relative w-[92%]">
            <div class="overflow-hidden rounded-lg bg-[#0f1115] p-1.5 shadow-[0_30px_60px_-30px_rgba(0,24,77,0.6)]">
              <div class="flex items-center gap-1.5 rounded-t bg-[#1d2027] px-2 py-1">
                <span class="truncate rounded bg-[#2a2e37] px-2 py-0.5 text-[10px] text-white/70">player.marien.co.id</span>
              </div>
              <img src="/shots/software/web-screen.webp" :alt="s.alt" class="block aspect-video w-full" loading="lazy" decoding="async" />
            </div>
            <div class="mx-auto h-2 w-1/4 rounded-b bg-[#0f1115]" aria-hidden="true" />
            <span class="absolute -right-2 -top-3 flex size-10 items-center justify-center rounded-full bg-white text-brand shadow-md ring-1 ring-line" aria-hidden="true">
              <IconLanguage class="size-6" />
            </span>
          </div>
        </div>

        <div class="flex flex-1 flex-col bg-white/70 p-6 sm:p-7">
          <h3 class="text-2xl leading-[1.15]">{{ s.name }}</h3>
          <p class="mt-2 leading-relaxed text-ink-muted">{{ s.text }}</p>
          <a
            :href="LINKS[i].href" :target="i === 1 ? undefined : '_blank'" rel="noopener"
            class="mt-auto inline-flex items-center gap-1.5 self-start pt-5 text-sm font-medium text-brand transition-colors hover:text-brand-strong"
            @click="track(LINKS[i].event, { location: 'software' })"
          >{{ s.link }}<IconArrow class="size-4" aria-hidden="true" /></a>
        </div>
      </li>
    </ul>
  </section>
</template>
