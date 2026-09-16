<script setup lang="ts">
/**
 * "Add media" as one surface: pick what you already have, or add what you don't, without
 * leaving the playlist you are in the middle of building.
 *
 * The library was previously the only thing on offer here, and its empty state told you to go
 * to the Media page and come back — which means abandoning a half-built playlist to upload one
 * logo. Uploading is therefore a tile in the same grid rather than a separate mode, and files
 * dropped anywhere on this dialog upload too.
 *
 * A finished upload arrives *selected*: you added it because you wanted it in this playlist,
 * so the Add button should already be counting it.
 */
import { computed, onMounted, ref } from 'vue'
import IconAddPhotoAlternateOutline from '~icons/material-symbols/add-photo-alternate-outline'
import IconCheck from '~icons/material-symbols/check'
import IconImageOutline from '~icons/material-symbols/image-outline'
import IconLanguage from '~icons/material-symbols/language'
import IconVideocam from '~icons/material-symbols/videocam'

import { useMediaUpload } from '@/hooks/useMediaUpload'
import AppButton from '@/reusables/AppButton.vue'
import AppModal from '@/reusables/AppModal.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import ProgressBar from '@/reusables/ProgressBar.vue'
import type { MediaRead } from '@/types/api'

const props = defineProps<{
  library: MediaRead[]
  isLoading?: boolean
  /** Files dropped on whatever opened this dialog, uploaded on open — so the drop gesture
   *  isn't silently thrown away on the way in. */
  initialFiles?: File[]
}>()
const emit = defineEmits<{ close: []; confirm: [MediaRead[]]; uploaded: [MediaRead] }>()

const KIND_ICON = { image: IconImageOutline, video: IconVideocam, web: IconLanguage } as const

const picked = ref<Set<string>>(new Set())
const query = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

const { jobs, add, isUploading } = useMediaUpload((media) => {
  emit('uploaded', media)
  picked.value = new Set(picked.value).add(media.id)
})

onMounted(() => {
  if (props.initialFiles?.length) add(props.initialFiles)
})

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  return q ? props.library.filter((m) => m.filename.toLowerCase().includes(q)) : props.library
})

function toggle(id: string) {
  const next = new Set(picked.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  picked.value = next
}

function onFiles(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) add(input.files)
  // Cleared so picking the same file twice still fires `change` the second time.
  input.value = ''
}

/** Depth-counted rather than a boolean: dragging across a child fires `dragleave` on the
 *  parent, and a plain flag makes the highlight flicker as the cursor crosses tiles. */
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
  if (e.dataTransfer?.files.length) add(e.dataTransfer.files)
}

function confirm() {
  // Library order rather than click order — the grid is what was just being looked at.
  emit('confirm', props.library.filter((m) => picked.value.has(m.id)))
}
</script>

<template>
  <AppModal title="Add media" size="xl" @close="emit('close')">
    <div
      class="flex flex-col gap-3"
      @dragenter.prevent="onDragEnter"
      @dragover.prevent
      @dragleave.prevent="onDragLeave"
      @drop.prevent="onDrop"
    >
      <input
        v-model="query"
        type="search"
        placeholder="Search your library"
        aria-label="Search your library"
        class="w-full rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm text-ink
               focus:border-ink focus:outline-none"
      />

      <div
        class="grid max-h-[55vh] grid-cols-2 gap-2 overflow-y-auto rounded-lg sm:grid-cols-4"
        :class="isDragOver ? 'outline outline-2 outline-dashed outline-ink' : ''"
      >
        <!-- Upload as a tile in the same grid, not a separate mode: adding a file you don't
             have yet is the same job as picking one you do. -->
        <button
          type="button"
          class="flex aspect-video flex-col items-center justify-center gap-0.5 rounded-lg border
                 border-dashed border-line-strong text-ink-muted transition-colors duration-200
                 hover:border-ink hover:text-ink"
          @click="fileInput?.click()"
        >
          <IconAddPhotoAlternateOutline class="size-5" />
          <span class="text-[12px]">Upload</span>
          <span class="text-[11px] text-ink-subtle">or drop files</span>
        </button>
        <input
          ref="fileInput" type="file" accept="image/*,video/*" multiple class="hidden"
          @change="onFiles"
        />

        <!-- In progress, in the grid, where the finished tile will be. -->
        <div
          v-for="job in jobs" :key="job.id"
          class="flex aspect-video flex-col justify-end rounded-lg bg-surface p-2"
        >
          <p class="truncate text-[12px] text-ink">{{ job.name }}</p>
          <p v-if="job.error" class="truncate text-[11px] text-danger" :title="job.error">
            {{ job.error }}
          </p>
          <ProgressBar v-else :value="job.progress" class="mt-1" />
        </div>

        <button
          v-for="m in filtered" :key="m.id"
          type="button"
          class="relative aspect-video overflow-hidden rounded-lg bg-raised"
          @click="toggle(m.id)"
        >
          <img
            v-if="m.thumbnail_url" :src="m.thumbnail_url" :alt="m.filename"
            class="size-full object-cover"
          />
          <component :is="KIND_ICON[m.kind]" class="absolute left-1.5 top-1.5 size-3.5 text-white/90" />
          <span
            class="absolute inset-x-0 bottom-0 truncate bg-black/55 px-1.5 py-1 text-left text-[11px]
                   text-white"
          >
            {{ m.filename }}
          </span>
          <span v-if="picked.has(m.id)" class="absolute inset-0 flex items-center justify-center bg-ink/40">
            <IconCheck class="size-6 text-white" />
          </span>
        </button>
      </div>

      <p v-if="isLoading" class="text-[13px] text-ink-muted">Loading library…</p>
      <p v-else-if="!library.length && !jobs.length" class="text-[13px] text-ink-muted">
        Nothing in your library yet. Upload here and it stays in the library for next time.
      </p>
      <p v-else-if="query && !filtered.length" class="text-[13px] text-ink-muted">Nothing matches that.</p>
    </div>

    <ModalActions>
      <AppButton variant="secondary" size="sm" @click="emit('close')">Cancel</AppButton>
      <!-- Disabled mid-upload: adding now would quietly leave the file still arriving out of
           the playlist, which reads as the upload having failed. -->
      <AppButton size="sm" :disabled="!picked.size || isUploading" @click="confirm">
        <IconCheck class="size-4" />
        Add {{ picked.size || '' }}
      </AppButton>
    </ModalActions>
  </AppModal>
</template>
