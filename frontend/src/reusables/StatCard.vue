<script setup lang="ts">
/**
 * One figure on the Overview, as a card: a label, the number, and a line of context under it.
 *
 * `tone="brand"` is the one card per row that carries the brand gradient — the logo's own
 * #002f96 → #0076dd — so the page has a single anchor of colour rather than four competing
 * ones. Everything else is a white card.
 *
 * `openable` adds a round button in the corner that emits `open` — for a figure you can go and
 * look at. Without it the card is just a figure.
 */
import SkeletonBlock from '@/reusables/SkeletonBlock.vue'

withDefaults(
  defineProps<{
    label: string
    value: string | number
    hint?: string
    tone?: 'plain' | 'brand' | 'danger'
    openable?: boolean
    /** The figure isn't known yet: placeholders stand in for the number and its line of context,
     *  rather than a "0" that reads as real. */
    loading?: boolean
  }>(),
  { tone: 'plain', openable: false, loading: false },
)
const emit = defineEmits<{ open: [] }>()
</script>

<template>
  <div
    class="relative flex flex-col justify-between rounded-2xl p-4 transition-colors duration-200"
    :class="tone === 'brand'
      ? 'bg-linear-to-br from-brand-strong to-brand-bright text-ink-inverse'
      : 'bg-canvas'"
  >
    <div class="flex items-start justify-between gap-2">
      <p class="text-[13px]" :class="tone === 'brand' ? 'text-ink-inverse/80' : 'text-ink-muted'">
        {{ label }}
      </p>
      <button
        v-if="openable"
        type="button"
        class="flex size-7 shrink-0 items-center justify-center rounded-full border transition-colors duration-150"
        :class="tone === 'brand'
          ? 'border-ink-inverse/40 text-ink-inverse hover:bg-ink-inverse/15'
          : 'border-line-strong text-ink-muted hover:border-brand hover:text-brand'"
        :aria-label="`Open ${label}`"
        @click="emit('open')"
      >
        <svg viewBox="0 0 16 16" class="size-3.5" fill="none" stroke="currentColor" stroke-width="1.7">
          <path d="M5 11 11 5M6 5h5v5" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </button>
    </div>
    <template v-if="loading">
      <span class="sr-only">{{ label }}: loading</span>
      <SkeletonBlock
        class="mt-3 h-7 w-14 rounded-md"
        :class="tone === 'brand' && 'bg-ink-inverse/25!'"
      />
      <SkeletonBlock
        class="mt-2.5 h-3 w-24 rounded-md"
        :class="tone === 'brand' && 'bg-ink-inverse/20!'"
      />
    </template>
    <template v-else>
    <p
      class="mt-2 font-display text-3xl tracking-tight"
      :class="tone === 'danger' ? 'text-danger' : tone === 'brand' ? 'text-ink-inverse' : 'text-ink'"
    >
      {{ value }}
    </p>
    <p
      v-if="hint"
      class="mt-1 text-[13px]"
      :class="tone === 'brand' ? 'text-ink-inverse/80' : 'text-ink-muted'"
    >
      {{ hint }}
    </p>
    </template>
  </div>
</template>
