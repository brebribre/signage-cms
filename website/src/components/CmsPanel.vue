<script setup lang="ts">
/**
 * A small, working slice of the CMS, sitting beside the totem: pick a playlist here and the
 * screen changes. It is the product's core loop in one gesture, and it is real interaction
 * rather than a screenshot of one.
 */
import IconCheck from '~icons/material-symbols/check'
import IconTv from '~icons/material-symbols/tv-outline'

import { SLIDES } from '@/data/slides'

defineProps<{ active: number }>()
const emit = defineEmits<{ select: [index: number] }>()
</script>

<template>
  <div class="w-full rounded-2xl border border-line bg-canvas p-3 shadow-[0_24px_60px_-24px_rgba(0,12,40,0.55)]">
    <div class="flex items-center justify-between gap-3 px-1 pb-2.5">
      <p class="flex items-center gap-1.5 text-[13px] text-ink">
        <IconTv class="size-4 text-ink-muted" aria-hidden="true" />
        Entrance totem
      </p>
      <span class="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-ink-subtle">
        <span class="size-1.5 rounded-full bg-emerald-500" /> Live
      </span>
    </div>
    <ul class="flex flex-col gap-1" role="radiogroup" aria-label="What this screen plays">
      <li v-for="(s, i) in SLIDES" :key="s.name">
        <button
          type="button"
          role="radio"
          :aria-checked="active === i"
          class="flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left transition-colors duration-150"
          :class="active === i ? 'bg-brand-soft' : 'hover:bg-surface'"
          @click="emit('select', i)"
        >
          <span
            class="size-8 shrink-0 overflow-hidden rounded-md bg-raised bg-cover bg-center"
            :style="s.src ? { backgroundImage: `url(${s.src})` } : { background: `linear-gradient(135deg, ${s.from}, ${s.to})` }"
            aria-hidden="true"
          />
          <span class="min-w-0 flex-1 truncate text-sm" :class="active === i ? 'text-brand' : 'text-ink'">{{ s.name }}</span>
          <IconCheck v-if="active === i" class="size-4 shrink-0 text-brand" aria-hidden="true" />
        </button>
      </li>
    </ul>
    <p class="px-2.5 pt-2 text-[11px] text-ink-subtle">Pick one. The screen changes.</p>
  </div>
</template>
