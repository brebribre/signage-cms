<script setup lang="ts">
/**
 * Wraps a list's placeholder rows: says "Loading …" to assistive tech once, and repeats the
 * default slot `count` times. The slot is the shape of one row — see DeviceCardSkeleton and
 * ListRowSkeleton — so each list keeps its own layout (a column of cards, a grid of tiles).
 */
withDefaults(defineProps<{ count?: number; label?: string }>(), { count: 4, label: 'Loading' })
</script>

<template>
  <div role="status" :aria-label="label" aria-busy="true">
    <span class="sr-only">{{ label }}…</span>
    <slot name="wrapper" :count="count">
      <div class="flex flex-col gap-2">
        <template v-for="i in count" :key="i"><slot :index="i - 1" /></template>
      </div>
    </slot>
  </div>
</template>
