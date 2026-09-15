<script setup lang="ts">
/** A new playlist — or more media into an existing one — without leaving the page it was
 *  opened from. Uploads land in the library and are picked automatically; anything already in
 *  the library can be picked too. The order things are picked in is the order they play. */
import { computed, ref } from 'vue'
import IconCheck from '~icons/material-symbols/check'
import IconClose from '~icons/material-symbols/close'

import { useMedia } from '@/hooks/useMedia'
import { useMediaUpload } from '@/hooks/useMediaUpload'
import { usePlaylistCompose } from '@/hooks/usePlaylistCompose'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppInput from '@/reusables/AppInput.vue'
import AppModal from '@/reusables/AppModal.vue'
import DropZone from '@/reusables/DropZone.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import ProgressBar from '@/reusables/ProgressBar.vue'
import type { PlaylistSummary } from '@/types/api'

const props = defineProps<{ playlist: PlaylistSummary | null }>()
const emit = defineEmits<{ saved: [id: string]; close: [] }>()

const { items: library, isLoading: libraryLoading, prepend } = useMedia()
const picked = ref<string[]>([])
const { jobs, isUploading, add, dismiss } = useMediaUpload((media) => {
  prepend(media)
  if (!picked.value.includes(media.id)) picked.value.push(media.id)
})
const { isSaving, error, compose } = usePlaylistCompose()

const name = ref('')

function togglePick(id: string) {
  const at = picked.value.indexOf(id)
  at >= 0 ? picked.value.splice(at, 1) : picked.value.push(id)
}
const order = (id: string) => picked.value.indexOf(id) + 1

const canSave = computed(
  () => !isUploading.value && (props.playlist ? picked.value.length > 0 : name.value.trim().length > 0),
)

async function onSave() {
  const id = await compose({ playlistId: props.playlist?.id ?? null, name: name.value, mediaIds: picked.value })
  if (id) emit('saved', id)
}
</script>

<template>
  <AppModal :title="playlist ? playlist.name : 'New playlist'" size="xl" @close="emit('close')">
    <form class="flex flex-col gap-4" @submit.prevent="onSave">
      <AppInput v-if="!playlist" id="compose-name" v-model="name" placeholder="Name" required />

      <DropZone accept="image/*,video/*" label="Drop images or videos" @files="add" />

      <ul v-if="jobs.length" class="flex flex-col gap-2">
        <li v-for="j in jobs" :key="j.id" class="flex items-center gap-3 text-[13px]">
          <span class="w-40 shrink-0 truncate text-ink">{{ j.name }}</span>
          <ProgressBar v-if="j.status !== 'failed'" class="flex-1" :value="j.progress" />
          <template v-else>
            <span class="min-w-0 flex-1 truncate text-danger" :title="j.error ?? ''">{{ j.error }}</span>
            <button type="button" class="text-ink-muted hover:text-ink" aria-label="Dismiss" @click="dismiss(j.id)">
              <IconClose class="size-4" />
            </button>
          </template>
        </li>
      </ul>

      <p v-if="libraryLoading && !library.length" class="text-sm text-ink-muted">Loading…</p>
      <div
        v-else-if="library.length"
        class="grid max-h-60 grid-cols-3 gap-2 overflow-y-auto p-1 sm:grid-cols-5"
      >
        <button
          v-for="m in library"
          :key="m.id"
          type="button"
          class="relative aspect-video overflow-hidden rounded-lg bg-raised transition-opacity duration-150"
          :class="order(m.id) ? 'ring-2 ring-ink ring-offset-2' : 'hover:opacity-80'"
          :title="m.filename"
          :aria-pressed="!!order(m.id)"
          @click="togglePick(m.id)"
        >
          <img v-if="m.thumbnail_url" :src="m.thumbnail_url" :alt="m.filename" class="size-full object-cover" loading="lazy" />
          <span v-else class="flex size-full items-center justify-center truncate px-1 text-[11px] text-ink-subtle">
            {{ m.filename }}
          </span>
          <span
            v-if="order(m.id)"
            class="absolute top-1 right-1 flex size-5 items-center justify-center rounded-full bg-ink
                   text-[11px] text-ink-inverse"
          >
            {{ order(m.id) }}
          </span>
        </button>
      </div>

      <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>

      <ModalActions>
        <span v-if="picked.length" class="mr-auto text-[13px] text-ink-muted">{{ picked.length }} selected</span>
        <AppButton variant="secondary" size="sm" type="button" @click="emit('close')">Cancel</AppButton>
        <AppButton size="sm" type="submit" :disabled="!canSave" :loading="isSaving">
          <IconCheck class="size-4" />
          {{ playlist ? 'Add' : 'Create' }}
        </AppButton>
      </ModalActions>
    </form>
  </AppModal>
</template>
