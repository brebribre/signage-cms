<script setup lang="ts">
/** A "⋮" button that opens a small menu of actions — for rows too narrow to show each action as
 *  its own button. Items go in the default slot, which receives `close` so an item can shut the
 *  menu once it has acted. Closes on a tap elsewhere or Escape. Clicks inside never reach the
 *  row underneath. */
import { onMounted, onUnmounted, ref } from 'vue'
import IconMoreVert from '~icons/material-symbols/more-vert'

defineProps<{ label?: string }>()

const open = ref(false)
const root = ref<HTMLElement | null>(null)

function close() {
  open.value = false
}
function onDocClick(e: MouseEvent) {
  if (open.value && root.value && !root.value.contains(e.target as Node)) close()
}
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') close()
}
onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div ref="root" class="relative" @click.stop>
    <button
      type="button"
      class="flex size-9 items-center justify-center rounded-full text-ink-muted transition-colors duration-150
             hover:bg-raised hover:text-ink"
      :aria-label="label ?? 'More actions'"
      aria-haspopup="menu"
      :aria-expanded="open"
      @click="open = !open"
    >
      <IconMoreVert class="size-5" />
    </button>
    <div
      v-if="open"
      role="menu"
      class="absolute right-0 z-20 mt-1 w-44 overflow-hidden rounded-xl border border-line bg-canvas p-1"
    >
      <slot :close="close" />
    </div>
  </div>
</template>
