<script setup lang="ts">
/**
 * The Paskall logo — the icon and wordmark together, as supplied (src/assets/paskall-logo.png is
 * the original; paskall-wordmark.png is it trimmed, on a transparent ground). An image rather than
 * type, so it's the brand's own letterforms and colour everywhere it appears.
 */
import wordmarkUrl from '@/assets/paskall-wordmark.png'

withDefaults(
  defineProps<{
    size?: 'sm' | 'md'
    align?: 'left' | 'center'
    /** `white` for a dark ground. The wordmark is one flat brand blue on transparent, so
     *  flattening it to black and inverting gives a clean white with its edges intact — no
     *  second asset to keep in step with the first. */
    tone?: 'brand' | 'white'
  }>(),
  { size: 'md', align: 'left', tone: 'brand' },
)
</script>

<template>
  <img
    :src="wordmarkUrl"
    alt="Paskall"
    draggable="false"
    class="block w-auto select-none"
    :class="[
      size === 'sm' ? 'h-6' : 'h-8',
      align === 'center' && 'mx-auto',
      tone === 'white' && 'brightness-0 invert',
    ]"
  />
</template>
