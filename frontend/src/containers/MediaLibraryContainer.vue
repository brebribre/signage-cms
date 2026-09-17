<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import IconDeleteOutline from '~icons/material-symbols/delete-outline'

import { useMedia } from '@/hooks/useMedia'
import { useMediaUpload } from '@/hooks/useMediaUpload'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppModal from '@/reusables/AppModal.vue'
import DropZone from '@/reusables/DropZone.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import FilterChip from '@/reusables/FilterChip.vue'
import MediaCard from '@/reusables/MediaCard.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import ProgressBar from '@/reusables/ProgressBar.vue'
import SkeletonBlock from '@/reusables/SkeletonBlock.vue'
import SkeletonList from '@/reusables/SkeletonList.vue'
import { ACCEPTED_MEDIA, SUPPORTED_FILE_TYPES } from '@/utils/mediaTypes'

const router = useRouter()
const { items, visible, counts, filter, isLoading, error, prepend, removeMany, refresh } = useMedia()

// A just-uploaded video shows "Optimising" until its playback copy exists — a few seconds to a
// few minutes, done on the server. Poll while any is, so the badge clears by itself.
const PROCESSING_POLL_MS = 5_000
const anyProcessing = computed(() => items.value.some((m) => m.kind === 'video' && !m.playback_ready))
let processingTimer: ReturnType<typeof setTimeout> | null = null
function stopProcessingPoll() {
  if (processingTimer !== null) clearTimeout(processingTimer)
  processingTimer = null
}
function scheduleProcessingPoll() {
  stopProcessingPoll()
  processingTimer = setTimeout(async () => {
    await refresh(true)
    if (anyProcessing.value) scheduleProcessingPoll()
  }, PROCESSING_POLL_MS)
}
watch(anyProcessing, (busy) => (busy ? scheduleProcessingPoll() : stopProcessingPoll()), { immediate: true })
onUnmounted(stopProcessingPoll)
const { jobs, active, isUploading, add, dismiss, clearFinished } = useMediaUpload(prepend)

// --- Selecting several, to delete them together ---

/** Select mode: a tap ticks a tile instead of opening it. A mode rather than checkboxes shown
 *  on hover, because there is no hover on a phone. */
const selecting = ref(false)
const selected = ref<Set<string>>(new Set())
/** Only what still exists — a file deleted elsewhere drops out of the count by itself. */
const selectedIds = computed(() => items.value.filter((m) => selected.value.has(m.id)).map((m) => m.id))
const allVisibleSelected = computed(
  () => visible.value.length > 0 && visible.value.every((m) => selected.value.has(m.id)),
)

function startSelecting() {
  selecting.value = true
  deleteResult.value = null
}
function stopSelecting() {
  selecting.value = false
  selected.value = new Set()
}
function toggle(id: string) {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}
/** Select all applies to what the filter shows; with everything shown already selected, it
 *  becomes "clear". */
function toggleAll() {
  const next = new Set(selected.value)
  if (allVisibleSelected.value) visible.value.forEach((m) => next.delete(m.id))
  else visible.value.forEach((m) => next.add(m.id))
  selected.value = next
}
function onTile(id: string) {
  if (selecting.value) toggle(id)
  else router.push({ name: 'media-detail', params: { id } })
}

// Escape leaves select mode, unless the confirm dialog is open (it closes itself first).
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape' && selecting.value && !confirming.value) stopSelecting()
}
onMounted(() => document.addEventListener('keydown', onKey))
onUnmounted(() => document.removeEventListener('keydown', onKey))

const confirming = ref(false)
const deleting = ref(false)
const deleteResult = ref<{ deleted: number; failed: { filename: string; reason: string }[] } | null>(null)

async function deleteSelected() {
  deleting.value = true
  try {
    deleteResult.value = await removeMany(selectedIds.value)
  } finally {
    deleting.value = false
    confirming.value = false
  }
  // Keep only what couldn't go, still selected, so it is obvious which ones they were.
  const remaining = new Set(items.value.map((m) => m.id))
  selected.value = new Set([...selected.value].filter((id) => remaining.has(id)))
  if (!selected.value.size) selecting.value = false
}
watch(filter, () => { deleteResult.value = null })

const STATUS_LABEL: Record<string, string> = {
  queued: 'Waiting',
  probing: 'Reading',
  uploading: 'Uploading',
  finishing: 'Finishing',
  done: 'Done',
  failed: 'Failed',
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle title="Media" :subtitle="`${counts.all} file${counts.all === 1 ? '' : 's'}`" />

    <DropZone
      :accept="ACCEPTED_MEDIA"
      label="Drop images or videos here"
      :hint="SUPPORTED_FILE_TYPES"
      @files="add"
    />

    <!-- Upload queue. Two run at once; the rest wait. -->
    <div v-if="jobs.length" class="flex flex-col gap-2">
      <div class="flex items-center justify-between">
        <p class="text-[13px] text-ink-muted">
          {{ isUploading ? `Uploading ${active.length}…` : 'Finished' }}
        </p>
        <!-- Successful rows remove themselves; this only ever clears failures the user has
             already read. -->
        <AppButton v-if="!isUploading" variant="ghost" size="sm" @click="clearFinished">
          Clear
        </AppButton>
      </div>
      <div v-for="job in jobs" :key="job.id" class="rounded-2xl bg-canvas p-4">
        <div class="flex items-baseline justify-between gap-3">
          <p class="truncate text-sm text-ink">{{ job.name }}</p>
          <p class="shrink-0 text-[13px]" :class="job.status === 'failed' ? 'text-danger' : 'text-ink-muted'">
            {{ STATUS_LABEL[job.status] }}
          </p>
        </div>
        <ProgressBar
          v-if="job.status === 'uploading' || job.status === 'probing' || job.status === 'finishing'"
          :value="job.progress"
          :indeterminate="job.status !== 'uploading'"
          class="mt-2"
        />
        <p v-if="job.error" class="mt-1.5 text-[13px] text-danger">{{ job.error }}</p>
        <AppButton v-if="job.status === 'failed'" variant="ghost" size="sm" class="mt-1.5"
                   @click="dismiss(job.id)">
          Dismiss
        </AppButton>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <FilterChip :active="filter === 'all'" :count="counts.all" @click="filter = 'all'">All</FilterChip>
      <FilterChip :active="filter === 'image'" :count="counts.image" @click="filter = 'image'">Images</FilterChip>
      <FilterChip :active="filter === 'video'" :count="counts.video" @click="filter = 'video'">Videos</FilterChip>
      <div class="ml-auto">
        <AppButton v-if="!selecting" variant="secondary" size="sm" :disabled="!counts.all" @click="startSelecting">
          Select
        </AppButton>
        <AppButton v-else variant="ghost" size="sm" @click="toggleAll">
          {{ allVisibleSelected ? 'Clear all' : 'Select all' }}
        </AppButton>
      </div>
    </div>

    <AppAlert v-if="deleteResult && deleteResult.failed.length" tone="danger">
      <p>
        {{ deleteResult.deleted ? `Deleted ${deleteResult.deleted}. ` : '' }}{{ deleteResult.failed.length }}
        couldn't be deleted — still selected below:
      </p>
      <ul class="mt-1 list-disc pl-5">
        <li v-for="f in deleteResult.failed" :key="f.filename">{{ f.filename }}: {{ f.reason }}</li>
      </ul>
    </AppAlert>
    <AppAlert v-else-if="deleteResult">
      Deleted {{ deleteResult.deleted }} file{{ deleteResult.deleted === 1 ? '' : 's' }}.
    </AppAlert>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>

    <!-- The same grid the tiles will fill, so nothing moves when they arrive. -->
    <SkeletonList v-if="isLoading" label="Loading media" :count="8">
      <template #wrapper="{ count }">
        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
          <div v-for="i in count" :key="i" class="relative">
            <span class="block pt-[100%]" aria-hidden="true" />
            <SkeletonBlock class="absolute! inset-0 rounded-2xl" />
          </div>
        </div>
      </template>
    </SkeletonList>

    <EmptyState
      v-else-if="!visible.length"
      title="Nothing here yet"
      :description="counts.all
        ? 'No files of this type. Try a different filter.'
        : 'Drop a file above to add it to the library.'"
    />

    <div v-else class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
      <MediaCard
        v-for="m in visible"
        :key="m.id"
        :filename="m.filename"
        :kind="m.kind"
        :thumbnail-url="m.thumbnail_url"
        :selectable="selecting"
        :selected="selected.has(m.id)"
        :processing="m.kind === 'video' && !m.playback_ready"
        @click="onTile(m.id)"
      />
    </div>

    <!-- The selection's actions, pinned to the bottom of the page while selecting, so they stay
         in reach however far down the library you scrolled to pick. -->
    <div
      v-if="selecting"
      class="sticky bottom-4 z-20 flex items-center gap-3 rounded-2xl bg-ink px-4 py-3 text-ink-inverse"
      role="region"
      aria-label="Selected media"
    >
      <p class="flex-1 text-sm" aria-live="polite">
        {{ selectedIds.length ? `${selectedIds.length} selected` : 'Tap files to select them' }}
      </p>
      <button type="button" class="text-sm text-ink-inverse/75 hover:text-ink-inverse" @click="stopSelecting">
        Cancel
      </button>
      <button
        type="button"
        class="inline-flex items-center gap-1.5 rounded-full bg-danger px-3.5 py-1.5 text-sm text-ink-inverse
               transition-opacity disabled:pointer-events-none disabled:opacity-40"
        :disabled="!selectedIds.length"
        @click="confirming = true"
      >
        <IconDeleteOutline class="size-4" aria-hidden="true" />
        Delete
      </button>
    </div>

    <AppModal
      v-if="confirming"
      :title="`Delete ${selectedIds.length} file${selectedIds.length === 1 ? '' : 's'}?`"
      @close="!deleting && (confirming = false)"
    >
      <p class="text-sm text-ink-muted">
        They're removed from the library for good. Anything still used in a playlist is skipped —
        remove it there first — and you'll see which ones.
      </p>
      <ModalActions>
        <AppButton variant="secondary" size="sm" :disabled="deleting" @click="confirming = false">Cancel</AppButton>
        <AppButton variant="danger" size="sm" :loading="deleting" @click="deleteSelected">
          Delete {{ selectedIds.length }}
        </AppButton>
      </ModalActions>
    </AppModal>
  </div>
</template>
