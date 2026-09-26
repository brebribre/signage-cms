<script setup lang="ts">
/** The cookie notice: a small card at the foot of the page until the visitor answers. Shown only
 *  when Google Analytics is set up (see useAnalytics). */
import { analyticsOn, consent, setConsent } from '@/composables/useAnalytics'
import { useI18n } from '@/i18n'

const { m } = useI18n()
</script>

<template>
  <div
    v-if="analyticsOn && !consent"
    class="fixed inset-x-3 bottom-3 z-50 mx-auto flex max-w-xl flex-col gap-3 rounded-2xl bg-white p-4 shadow-[0_20px_60px_-20px_rgba(0,24,77,0.45)] ring-1 ring-line sm:bottom-5 sm:flex-row sm:items-center sm:gap-5 sm:p-5"
    role="region" :aria-label="m.consent.label"
  >
    <p class="text-sm leading-relaxed text-ink-muted">{{ m.consent.text }}</p>
    <div class="flex shrink-0 gap-2">
      <button type="button" class="flex-1 rounded-lg px-4 py-2.5 text-sm font-medium text-ink ring-1 ring-ink/70 transition-colors hover:bg-ink hover:text-white sm:flex-none" @click="setConsent('denied')">{{ m.consent.decline }}</button>
      <button type="button" class="flex-1 rounded-lg bg-action px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-action-hover sm:flex-none" @click="setConsent('granted')">{{ m.consent.accept }}</button>
    </div>
  </div>
</template>
