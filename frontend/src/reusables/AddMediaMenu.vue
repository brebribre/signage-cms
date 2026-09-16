<script setup lang="ts">
/**
 * "Add media" as a split button: the thing people do almost every time — put something from
 * the library, or a file off their desktop, into this playlist — is one click, and the two
 * rarer destinations (a live website, a custom multi-element scene) sit behind the caret.
 *
 * It used to be a plain dropdown, which made every path two clicks including the common one,
 * and led only to a picker of things you already had. Files dropped on it now go straight into
 * that picker, already uploading.
 */
import { onMounted, onUnmounted, ref } from 'vue'
import IconAddPhotoAlternateOutline from '~icons/material-symbols/add-photo-alternate-outline'
import IconKeyboardArrowDown from '~icons/material-symbols/keyboard-arrow-down'
import IconLanguage from '~icons/material-symbols/language'

import AppButton from '@/reusables/AppButton.vue'

withDefaults(defineProps<{
  label?: string
  size?: 'sm' | 'md'
  /** `block`: a big full-width target, for the end of a list rather than a toolbar. */
  variant?: 'pill' | 'block'
}>(), {
  label: 'Add media',
  size: 'sm',
  variant: 'pill',
})
const emit = defineEmits<{
  'use-existing': []
  'add-website': []
  'create-custom': []
  /** Dropped straight onto the button — the picker opens with these already uploading. */
  files: [File[]]
}>()

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

function pick(kind: 'website' | 'custom') {
  open.value = false
  if (kind === 'website') emit('add-website')
  else emit('create-custom')
}

/** Depth-counted — see MediaPicker for why a boolean flickers. */
let dragDepth = 0
const isDragOver = ref(false)
function onDragEnter() {
  dragDepth++
  isDragOver.value = true
}
function onDragLeave() {
  dragDepth--
  if (dragDepth <= 0) isDragOver.value = false
}
function onDrop(e: DragEvent) {
  dragDepth = 0
  isDragOver.value = false
  const files = Array.from(e.dataTransfer?.files ?? [])
  if (files.length) emit('files', files)
}
</script>

<template>
  <div ref="root" class="relative" :class="variant === 'block' ? 'block w-full' : 'inline-block'">
    <div v-if="variant === 'block'" class="flex w-full items-stretch gap-1.5">
      <button
        type="button"
        class="flex flex-1 flex-wrap items-center justify-center gap-2 rounded-xl border border-dashed
               bg-surface py-5 text-sm text-ink transition-colors duration-200 hover:border-ink hover:bg-raised"
        :class="isDragOver ? 'border-ink bg-raised' : 'border-line-strong'"
        @click="emit('use-existing')"
        @dragenter.prevent="onDragEnter"
        @dragover.prevent
        @dragleave.prevent="onDragLeave"
        @drop.prevent="onDrop"
      >
        <IconAddPhotoAlternateOutline class="size-5" />
        {{ label }}
        <span class="text-[12px] text-ink-subtle">or drop files here</span>
      </button>
      <button
        type="button"
        aria-label="Other ways to add"
        :aria-expanded="open"
        class="rounded-xl border border-dashed border-line-strong bg-surface px-3 text-ink-muted
               transition-colors duration-200 hover:border-ink hover:text-ink"
        @click="open = !open"
      >
        <IconKeyboardArrowDown class="size-4" />
      </button>
    </div>

    <div v-else class="inline-flex items-center gap-1">
      <AppButton variant="secondary" :size="size" @click="emit('use-existing')">
        <IconAddPhotoAlternateOutline class="size-4" />
        {{ label }}
      </AppButton>
      <AppButton
        variant="secondary" :size="size" aria-label="Other ways to add" :aria-expanded="open"
        @click="open = !open"
      >
        <IconKeyboardArrowDown class="size-4" />
      </AppButton>
    </div>

    <div
      v-if="open"
      class="absolute right-0 z-10 mt-2 w-52 overflow-hidden rounded-xl border border-line bg-canvas p-1"
    >
      <button
        type="button"
        class="flex w-full items-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors
               duration-150 hover:bg-surface"
        @click="pick('website')"
      >
        <IconLanguage class="mt-0.5 size-4 shrink-0 text-ink-muted" />
        <span class="min-w-0">
          <span class="block text-sm text-ink">Website</span>
          <span class="block truncate text-[12px] text-ink-subtle">Show a web page live</span>
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
