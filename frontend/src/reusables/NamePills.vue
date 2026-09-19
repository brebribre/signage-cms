<script setup lang="ts">
/**
 * A few names as pills, the rest folded into "+n" — for a row that must stay one line high
 * however many screens or playlists a change touches. Hovering "+n" lists the rest.
 */
import { computed } from 'vue'
import type { Component } from 'vue'

const props = withDefaults(defineProps<{
  names: string[]
  icon: Component
  /** What the names are, for the empty case: "No screens". */
  noun: string
  max?: number
}>(), { max: 2 })

const shown = computed(() => props.names.slice(0, props.max))
const rest = computed(() => props.names.slice(props.max))
</script>

<template>
  <ul class="flex min-w-0 flex-wrap items-center gap-1.5" :aria-label="`${names.length} ${noun}`">
    <li v-if="!names.length" class="flex items-center gap-1 text-[12px] text-ink-subtle">
      <component :is="icon" class="size-3.5" aria-hidden="true" />No {{ noun }}
    </li>
    <li
      v-for="name in shown" :key="name"
      class="flex max-w-[14rem] items-center gap-1 rounded-full bg-raised px-2.5 py-0.5 text-[12px] text-ink"
    >
      <component :is="icon" class="size-3.5 shrink-0 text-ink-muted" aria-hidden="true" />
      <span class="truncate">{{ name }}</span>
    </li>
    <li
      v-if="rest.length"
      class="rounded-full bg-raised px-2 py-0.5 text-[12px] tabular-nums text-ink-muted"
      :title="rest.join(', ')"
    >
      +{{ rest.length }}
    </li>
  </ul>
</template>
