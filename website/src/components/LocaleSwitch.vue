<script setup lang="ts">
/** EN | ID: the two languages side by side, the current one filled. */
import { track } from '@/composables/useAnalytics'
import { LOCALES, useI18n } from '@/i18n'

const { locale, m, setLocale } = useI18n()
</script>

<template>
  <div
    class="inline-flex rounded-lg bg-white/80 p-0.5 text-xs font-medium ring-1 ring-line-strong backdrop-blur"
    role="group" :aria-label="m.lang.label"
  >
    <button
      v-for="l in LOCALES" :key="l"
      type="button" :lang="l" :aria-pressed="locale === l" :title="m.lang[l]"
      class="rounded-md px-2.5 py-1 uppercase transition-colors"
      :class="locale === l ? 'bg-brand-deep text-white' : 'text-ink-muted hover:text-ink'"
      @click="setLocale(l); track('language_switch', { language: l })"
    >{{ l }}</button>
  </div>
</template>
