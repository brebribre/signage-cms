<script setup lang="ts">
/**
 * The Paskall logo — the icon and wordmark together, as supplied (src/assets/paskall-logo.png is
 * the original; paskall-wordmark.png is it trimmed, on a transparent ground). An image rather than
 * type, so it's the brand's own letterforms and colour everywhere it appears.
 */
import wordmarkUrl from '@/assets/paskall-wordmark.png'

withDefaults(defineProps<{ size?: 'sm' | 'md'; align?: 'left' | 'center' }>(), {
  size: 'md',
  align: 'left',
})
</script>

<template>
  <img
    :src="wordmarkUrl"
    alt="Paskall"
    draggable="false"
    class="block w-auto select-none"
    :class="[size === 'sm' ? 'h-6' : 'h-8', align === 'center' && 'mx-auto']"
  />
</template>
