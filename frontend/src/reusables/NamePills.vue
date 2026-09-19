<script setup lang="ts">
/**
 * A few names as pills, the rest folded into "+n" — for a row that must stay one line high
 * however many screens or playlists a change touches. Hovering "+n" lists the rest. The row's
 * own label (an icon beside it) says what the names are; the pills carry only the names.
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  names: string[]
  /** What the names are, for the empty case: "No screens". */
  noun: string
  max?: number
}>(), { max: 2 })

const shown = computed(() => props.names.slice(0, props.max))
const rest = computed(() => props.names.slice(props.max))
</script>

<template>
  <ul class="flex min-w-0 flex-wrap items-center gap-1.5" :aria-label="`${names.length} ${noun}`">
    <li v-if="!names.length" class="text-[12px] text-ink-subtle">No {{ noun }}</li>
    <li
      v-for="name in shown" :key="name"
      class="max-w-[14rem] truncate rounded-full bg-raised px-2.5 py-0.5 text-[12px] text-ink"
    >
      {{ name }}
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
