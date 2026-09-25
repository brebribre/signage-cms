<script setup lang="ts">
/** A screenshot in a thin browser chrome, so a product image reads as the product. Pass `src`
 *  for a single shot, or fill the slot when the frame holds something that changes. The caller
 *  rounds its corners, since which ones depends on which card edge it runs off. */
defineProps<{ src?: string; alt?: string; label?: string }>()
</script>

<template>
  <figure class="overflow-hidden border border-line bg-canvas shadow-[0_30px_80px_-30px_rgba(0,24,77,0.35)]">
    <div class="flex items-center gap-1.5 border-b border-line bg-surface px-3.5 py-2.5">
      <span class="size-2.5 rounded-full bg-line-strong" /><span class="size-2.5 rounded-full bg-line-strong" /><span class="size-2.5 rounded-full bg-line-strong" />
      <span v-if="label" class="ml-3 rounded-md bg-canvas px-2 py-0.5 text-[11px] text-ink-subtle">{{ label }}</span>
    </div>
    <slot>
      <img v-if="src" :src="src" :alt="alt" class="block w-full" loading="lazy" decoding="async" />
    </slot>
  </figure>
</template>
