<script setup lang="ts">
/** Choosing a playlist by what's in it, not just its name — the first thumbnail rides along in
 *  the button and in every option. "New playlist" sits at the bottom of the same list, so there
 *  is no second place to look when the right one doesn't exist yet. */
import { computed, onMounted, onUnmounted, ref } from 'vue'
import IconAdd from '~icons/material-symbols/add'
import IconCheck from '~icons/material-symbols/check'
import IconExpandMore from '~icons/material-symbols/expand-more'

import type { PlaylistSummary } from '@/types/api'

const props = defineProps<{ playlists: PlaylistSummary[]; invalid?: boolean }>()
const emit = defineEmits<{ create: [] }>()
const model = defineModel<string>({ default: '' })

const open = ref(false)
const root = ref<HTMLElement | null>(null)
const selected = computed(() => props.playlists.find((p) => p.id === model.value) ?? null)

function onDocClick(e: MouseEvent) {
  if (open.value && root.value && !root.value.contains(e.target as Node)) open.value = false
}
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') open.value = false
}
onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKey)
})

function choose(id: string) {
  model.value = id
  open.value = false
}
function create() {
  open.value = false
  emit('create')
}
</script>

<template>
  <div ref="root" class="relative">
    <button
      type="button"
      class="flex w-full items-center gap-2.5 rounded-lg border bg-canvas py-1.5 pr-2 pl-1.5 text-left text-sm
             transition-colors duration-150 focus:border-ink focus:outline-none"
      :class="invalid ? 'border-danger' : 'border-line-strong'"
      :aria-expanded="open"
      @click="open = !open"
    >
      <span class="h-7 w-12 shrink-0 overflow-hidden rounded-md bg-raised">
        <img v-if="selected?.thumbnails[0]" :src="selected.thumbnails[0]" class="size-full object-cover" />
      </span>
      <span class="min-w-0 flex-1 truncate" :class="selected ? 'text-ink' : 'text-ink-subtle'">
        {{ selected?.name ?? 'Playlist' }}
      </span>
      <IconExpandMore class="size-4 shrink-0 text-ink-muted" />
    </button>

    <div
      v-if="open"
      class="absolute left-0 z-20 mt-1 w-full min-w-64 overflow-hidden rounded-xl border border-line bg-canvas p-1"
    >
      <ul v-if="playlists.length" class="max-h-64 overflow-y-auto border-b border-line pb-1">
        <li v-for="p in playlists" :key="p.id">
          <button
            type="button"
            class="flex w-full items-center gap-2.5 rounded-lg px-1.5 py-1.5 text-left transition-colors
                   duration-150 hover:bg-surface"
            @click="choose(p.id)"
          >
            <span class="h-7 w-12 shrink-0 overflow-hidden rounded-md bg-raised">
              <img v-if="p.thumbnails[0]" :src="p.thumbnails[0]" class="size-full object-cover" loading="lazy" />
            </span>
            <span class="min-w-0 flex-1 truncate text-sm text-ink">{{ p.name }}</span>
            <IconCheck v-if="p.id === model" class="size-4 shrink-0 text-ink" />
          </button>
        </li>
      </ul>
      <button
        type="button"
        class="flex w-full items-center gap-2.5 rounded-lg px-1.5 py-2 text-left text-sm text-ink transition-colors
               duration-150 hover:bg-surface"
        :class="playlists.length ? 'mt-1' : ''"
        @click="create"
      >
        <span class="flex h-7 w-12 shrink-0 items-center justify-center"><IconAdd class="size-4" /></span>
        New playlist
      </button>
    </div>
  </div>
</template>
