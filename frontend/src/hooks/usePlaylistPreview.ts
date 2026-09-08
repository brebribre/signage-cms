import { computed, onUnmounted, ref, watch } from 'vue'

import type { DraftItem } from '@/hooks/usePlaylistEditor'

/**
 * Steps through a playlist's enabled items at their real durations, so the preview shows
 * the loop rather than a still.
 *
 * Deliberately drives off the **draft**, not the saved playlist: the point is to see an
 * unsaved change before committing it to a wall of screens.
 */
export function usePlaylistPreview(draft: () => DraftItem[]) {
  const index = ref(0)
  const isPlaying = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null

  const enabled = computed(() => draft().filter((d) => d.isEnabled))
  const current = computed(() => enabled.value[index.value] ?? enabled.value[0] ?? null)

  function clear() {
    if (timer) clearTimeout(timer)
    timer = null
  }

  function schedule() {
    clear()
    const item = current.value
    if (!isPlaying.value || !item || enabled.value.length === 0) return
    timer = setTimeout(() => {
      index.value = (index.value + 1) % Math.max(1, enabled.value.length)
      schedule()
    }, item.durationSeconds * 1000)
  }

  function play() {
    if (!enabled.value.length) return
    isPlaying.value = true
    schedule()
  }

  function pause() {
    isPlaying.value = false
    clear()
  }

  function toggle() {
    isPlaying.value ? pause() : play()
  }

  /** Jump to an item — clicking a row should preview that row. */
  function select(item: DraftItem) {
    const at = enabled.value.findIndex((d) => d.key === item.key)
    if (at >= 0) {
      index.value = at
      if (isPlaying.value) schedule()
    }
  }

  // Editing the list underneath a running preview must not leave the index past the end.
  watch(enabled, (list) => {
    if (index.value >= list.length) index.value = 0
    if (isPlaying.value) schedule()
  })

  onUnmounted(clear)

  return { index, isPlaying, current, enabled, play, pause, toggle, select }
}
