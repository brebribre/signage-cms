<script setup lang="ts">
/**
 * Cards carry no border. The surface tint is what separates a card from the page; an
 * outline on top of it states the same thing twice and turns a stack of cards into a grid
 * of boxes. fortu.co.id uses no shadows at all, so neither does this.
 *
 * An interactive card therefore cannot signal hover by brightening its edge — it deepens
 * its surface instead.
 */
withDefaults(defineProps<{ interactive?: boolean; padded?: boolean }>(), {
  interactive: false,
  padded: true,
})
</script>

<template>
  <div
    class="rounded-xl bg-surface transition-colors duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]"
    :class="[padded && 'p-4', interactive && 'cursor-pointer hover:bg-raised']"
  >
    <slot />
  </div>
</template>
