<script setup lang="ts">
/**
 * One of the big rounded pastel cards the features live in: the thing itself on one side, a
 * small outlined tag, a heading and the words on the other. `reverse` swaps the sides so a run
 * of cards zigzags rather than marching down one edge.
 */
defineProps<{ tone: 'tint' | 'sky'; tag: string; reverse?: boolean }>()
</script>

<template>
  <div
    class="reveal overflow-hidden rounded-[2rem] p-6 sm:rounded-[2.5rem] sm:p-10 lg:p-14"
    :class="tone === 'tint' ? 'bg-tint' : 'bg-sky'"
  >
    <div class="grid grid-cols-1 items-center gap-8 lg:grid-cols-2 lg:gap-16">
      <!-- Under the words on a phone; beside them, on either side, on a wide page. -->
      <div class="order-last min-w-0" :class="reverse ? 'lg:order-last' : 'lg:order-first'">
        <slot name="visual" />
      </div>
      <div class="min-w-0">
        <span class="tag text-brand-deep">{{ tag }}</span>
        <slot />
      </div>
    </div>
  </div>
</template>
