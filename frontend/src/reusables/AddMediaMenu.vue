<script setup lang="ts">
/** "Add media" as a button with two destinations, used both on the playlist row list and
 *  its empty state: an existing single media item straight from the library, or a new
 *  custom scene built on the full-page canvas editor. */
import { onMounted, onUnmounted, ref } from 'vue'
import IconAddPhotoAlternateOutline from '~icons/material-symbols/add-photo-alternate-outline'
import IconPhotoLibraryOutline from '~icons/material-symbols/photo-library-outline'

import AppButton from '@/reusables/AppButton.vue'

withDefaults(defineProps<{ label?: string; size?: 'sm' | 'md' }>(), {
  label: 'Add media',
  size: 'sm',
})
const emit = defineEmits<{ 'use-existing': []; 'create-custom': [] }>()

const open = ref(false)
const root = ref<HTMLElement | null>(null)

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

function pick(kind: 'existing' | 'custom') {
  open.value = false
  if (kind === 'existing') emit('use-existing')
  else emit('create-custom')
}
</script>

<template>
  <div ref="root" class="relative inline-block">
    <AppButton variant="secondary" :size="size" @click="open = !open">
      <IconAddPhotoAlternateOutline class="size-4" />
      {{ label }}
    </AppButton>

    <div
      v-if="open"
      class="absolute right-0 z-10 mt-2 w-52 overflow-hidden rounded-xl border border-line bg-canvas p-1"
    >
      <button
        type="button"
        class="flex w-full items-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors
               duration-150 hover:bg-surface"
        @click="pick('existing')"
      >
        <IconPhotoLibraryOutline class="mt-0.5 size-4 shrink-0 text-ink-muted" />
        <span class="min-w-0">
          <span class="block text-sm text-ink">Use existing</span>
          <span class="block truncate text-[12px] text-ink-subtle">Pick from your library</span>
        </span>
      </button>
      <button
        type="button"
        class="flex w-full items-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors
               duration-150 hover:bg-surface"
        @click="pick('custom')"
      >
        <IconAddPhotoAlternateOutline class="mt-0.5 size-4 shrink-0 text-ink-muted" />
        <span class="min-w-0">
          <span class="block text-sm text-ink">Create custom</span>
          <span class="block truncate text-[12px] text-ink-subtle">Build a scene on the canvas</span>
        </span>
      </button>
    </div>
  </div>
</template>
