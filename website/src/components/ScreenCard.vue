<script setup lang="ts">
/**
 * One screen in the fleet round the hero's CMS: a small card with the screen at its real
 * shape, playing whatever the CMS has on air, and its name under it. The new slide pushes the
 * old one out, a little later on each screen, the way a fleet actually updates.
 */
import { SLIDES } from '@/data/slides'

defineProps<{ active: number; name: string; kind: string; portrait?: boolean; delay?: number }>()
</script>

<template>
  <div class="rounded-3xl bg-white p-2.5 shadow-[0_24px_60px_-28px_rgba(0,24,77,0.45)] ring-1 ring-line">
    <div
      class="relative overflow-hidden rounded-2xl bg-brand-deep ring-4 ring-[#0b0e14]"
      :class="portrait ? 'aspect-video lg:aspect-[9/14]' : 'aspect-video'"
      :style="{ '--swap-delay': `${delay ?? 0}ms` }"
    >
      <Transition name="swap">
        <div :key="active" class="absolute inset-0">
          <img v-if="SLIDES[active].src" :src="SLIDES[active].src" alt="" class="size-full object-cover" decoding="async" />
          <div v-else class="size-full" :style="{ background: `linear-gradient(150deg, ${SLIDES[active].from}, ${SLIDES[active].to})` }" />
          <div class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/70 to-transparent px-3 pb-2.5 pt-8">
            <p class="display truncate text-sm leading-tight text-white">{{ SLIDES[active].title }}</p>
            <p class="truncate text-[10px] text-white/75">{{ SLIDES[active].sub }}</p>
          </div>
        </div>
      </Transition>
    </div>
    <div class="flex items-center justify-between gap-2 px-1 pt-2.5 pb-0.5">
      <span class="min-w-0">
        <span class="block truncate text-[13px] text-ink">{{ name }}</span>
        <span class="block truncate text-[11px] text-ink-subtle">{{ kind }}</span>
      </span>
      <span class="size-2 shrink-0 rounded-full bg-emerald-500" aria-label="Online" />
    </div>
  </div>
</template>
