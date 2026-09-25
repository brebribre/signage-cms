<script setup lang="ts">
/**
 * A small, working slice of the CMS beside the totem: lettered pills, one per playlist. Pick
 * one and the screen changes. It is the product's core loop in one gesture, and real
 * interaction rather than a screenshot of one.
 */
import { SLIDES } from '@/data/slides'

defineProps<{ active: number }>()
const emit = defineEmits<{ select: [index: number] }>()
</script>

<template>
  <ul class="flex flex-col gap-2.5" role="radiogroup" aria-label="What the screen plays">
    <li v-for="(s, i) in SLIDES" :key="s.name">
      <button
        type="button" role="radio" :aria-checked="active === i"
        class="flex w-full items-center gap-2.5 rounded-full py-1.5 pl-1.5 pr-5 text-left shadow-[0_10px_30px_-18px_rgba(0,24,77,0.5)] ring-1 backdrop-blur transition-all duration-200"
        :class="active === i ? 'bg-brand-deep text-white ring-brand-deep' : 'bg-white/85 text-ink ring-line hover:ring-line-strong'"
        @click="emit('select', i)"
      >
        <span
          class="inline-flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold"
          :class="active === i ? 'bg-accent text-brand-deep' : 'bg-sky-strong text-brand-deep'"
        >{{ String.fromCharCode(65 + i) }}</span>
        <span class="truncate text-sm">{{ s.name }}</span>
      </button>
    </li>
  </ul>
</template>
