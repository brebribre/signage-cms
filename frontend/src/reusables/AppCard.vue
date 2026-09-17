<script setup lang="ts">
/**
 * A white card on the page's tint. No border and no shadow: the contrast between white and the
 * tinted page is the whole edge, which keeps a stack of cards calm rather than a grid of boxes.
 * An interactive card deepens on hover.
 */
withDefaults(defineProps<{ interactive?: boolean; padded?: boolean }>(), {
  interactive: false,
  padded: true,
})
</script>

<template>
  <div
    class="rounded-2xl bg-canvas transition-colors duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]"
    :class="[padded && 'p-4', interactive && 'cursor-pointer hover:bg-surface']"
  >
    <slot />
  </div>
</template>
