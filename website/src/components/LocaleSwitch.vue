<script setup lang="ts">
/** EN | ID: the two languages side by side, the current one filled. */
import { LOCALES, useI18n } from '@/i18n'

defineProps<{ inverse?: boolean }>()
const { locale, m, setLocale } = useI18n()
</script>

<template>
  <div
    class="inline-flex rounded-full p-0.5 text-xs font-medium ring-1"
    :class="inverse ? 'ring-white/30' : 'ring-line-strong'"
    role="group" :aria-label="m.lang.label"
  >
    <button
      v-for="l in LOCALES" :key="l"
      type="button" :lang="l" :aria-pressed="locale === l" :title="m.lang[l]"
      class="rounded-full px-2.5 py-1 uppercase transition-colors"
      :class="locale === l
        ? (inverse ? 'bg-white text-brand-deep' : 'bg-brand-deep text-white')
        : (inverse ? 'text-white/80 hover:text-white' : 'text-ink-muted hover:text-ink')"
      @click="setLocale(l)"
    >{{ l }}</button>
  </div>
</template>
