<script setup lang="ts">
/**
 * A row of thumbnails that shows as many as fit, and says how many more there are.
 *
 * It measures its own width (ResizeObserver) rather than guessing at breakpoints, so the count
 * follows the space it is actually given — a wide window shows more, a phone fewer, and a long
 * line of text beside it takes precedence. When not everything fits, the last slot becomes "+m",
 * counting every hidden item — `total` can exceed the thumbnails provided (the server sends only
 * the first few).
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    thumbnails: (string | null)[]
    /** How many items there are in all. Defaults to the thumbnails given. */
    total?: number
    /** Tile edge in px, and the gap between tiles — kept in step with the classes below. */
    tile?: number
    gap?: number
  }>(),
  { tile: 56, gap: 6 },
)

const root = ref<HTMLElement | null>(null)
const capacity = ref(0)

let observer: ResizeObserver | null = null
onMounted(() => {
  observer = new ResizeObserver(([entry]) => {
    const width = entry.contentRect.width
    capacity.value = Math.max(1, Math.floor((width + props.gap) / (props.tile + props.gap)))
  })
  if (root.value) observer.observe(root.value)
})
onBeforeUnmount(() => observer?.disconnect())

const total = computed(() => Math.max(props.total ?? 0, props.thumbnails.length))

/** Thumbnails to draw, and the "+m" count (0 when everything fits). */
const layout = computed(() => {
  const available = Math.min(capacity.value, props.thumbnails.length)
  if (total.value <= capacity.value && available === total.value) {
    return { shown: props.thumbnails.slice(0, available), more: 0 }
  }
  // Something is hidden: one slot goes to the count, so it is always visible.
  const shown = props.thumbnails.slice(0, Math.max(0, Math.min(available, capacity.value - 1)))
  return { shown, more: total.value - shown.length }
})
</script>

<template>
  <div ref="root" class="flex min-w-0 gap-1.5 overflow-hidden" :aria-label="`${total} items`">
    <div
      v-for="(url, i) in layout.shown"
      :key="i"
      class="size-14 shrink-0 overflow-hidden rounded-lg bg-raised"
    >
      <img v-if="url" :src="url" alt="" class="size-full object-cover" loading="lazy" />
    </div>
    <div
      v-if="layout.more"
      class="flex size-14 shrink-0 items-center justify-center rounded-lg bg-surface text-[13px] font-medium text-ink-muted"
      :title="`${layout.more} more`"
    >
      +{{ layout.more }}
    </div>
  </div>
</template>
