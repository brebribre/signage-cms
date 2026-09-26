<script setup lang="ts">
/**
 * Setting up the device, as the first of the feature cards: the player on the screen (the Android app,
 * or the web player in a smart TV's browser) and the CMS to run it from, two numbered steps in
 * one card, each with the link that does it. Full width on a wide page, the words beside the
 * steps; stacked on a phone.
 */
import IconAndroid from '~icons/material-symbols/android'
import IconArrow from '~icons/material-symbols/arrow-outward'
import IconTv from '~icons/material-symbols/connected-tv-outline'

import { track } from '@/composables/useAnalytics'
import { useI18n } from '@/i18n'

const { m } = useI18n()
/** The latest APK the fleet runs (a redirect to it), the web player, and the CMS. */
/** The Android player's download page, with every version. */
const APK = '/android'
const WEB_PLAYER = 'https://player.marien.co.id'
const CMS = 'https://app.marien.co.id'
const PRIMARY = 'inline-flex items-center justify-center gap-2 rounded-lg bg-action px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-action-hover'
const SECONDARY = 'inline-flex items-center justify-center gap-2 rounded-lg bg-white px-5 py-3 text-sm font-medium text-ink ring-1 ring-ink/70 transition-colors hover:bg-ink hover:text-white'
</script>

<template>
  <section id="start">
    <article class="relative grid gap-8 overflow-hidden rounded-2xl bg-brand-soft p-6 ring-1 ring-tint-strong/60 sm:p-8 lg:grid-cols-[0.8fr_1.6fr] lg:gap-10 lg:p-10">
      <div>
        <h3 class="text-3xl leading-[1.1] sm:text-4xl">{{ m.start.title }}</h3>
        <p class="mt-3 max-w-sm leading-relaxed text-ink-muted">{{ m.start.body }}</p>
      </div>

      <ol class="grid gap-3 sm:gap-4 md:grid-cols-2">
        <li class="flex flex-col rounded-xl bg-white/90 p-5 shadow-[0_20px_50px_-30px_rgba(0,24,77,0.5)] ring-1 ring-white sm:p-6">
          <span class="display flex size-9 items-center justify-center rounded-full bg-gradient-to-br from-brand-strong to-brand-bright text-white">1</span>
          <p class="display mt-4 text-xl leading-snug text-ink">{{ m.start.player.title }}</p>
          <p class="mt-1.5 text-sm leading-relaxed text-ink-muted">{{ m.start.player.text }}</p>
          <div class="mt-auto flex flex-col gap-2 pt-5 sm:flex-row sm:flex-wrap">
            <a :href="APK" :class="PRIMARY" @click="track('android_page_click', { location: 'start' })"><IconAndroid class="size-5" aria-hidden="true" />{{ m.start.player.android }}</a>
            <a :href="WEB_PLAYER" target="_blank" rel="noopener" :class="SECONDARY" @click="track('open_web_player')"><IconTv class="size-5" aria-hidden="true" />{{ m.start.player.web }}</a>
          </div>
        </li>
        <li class="flex flex-col rounded-xl bg-white/90 p-5 shadow-[0_20px_50px_-30px_rgba(0,24,77,0.5)] ring-1 ring-white sm:p-6">
          <span class="display flex size-9 items-center justify-center rounded-full bg-gradient-to-br from-brand-strong to-brand-bright text-white">2</span>
          <p class="display mt-4 text-xl leading-snug text-ink">{{ m.start.cms.title }}</p>
          <p class="mt-1.5 text-sm leading-relaxed text-ink-muted">{{ m.start.cms.text }}</p>
          <div class="mt-auto flex flex-col gap-2 pt-5 sm:flex-row">
            <a :href="CMS" target="_blank" rel="noopener" :class="SECONDARY" @click="track('open_cms')">{{ m.start.cms.open }}<IconArrow class="size-5" aria-hidden="true" /></a>
          </div>
        </li>
      </ol>
    </article>
  </section>
</template>
