<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import IconDeleteOutline from '~icons/material-symbols/delete-outline'
import IconUpload from '~icons/material-symbols/upload'

import { useFleetHealth } from '@/hooks/useFleetHealth'
import { useFormat } from '@/hooks/useFormat'
import { useMedia } from '@/hooks/useMedia'
import { useMediaUpload } from '@/hooks/useMediaUpload'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppModal from '@/reusables/AppModal.vue'
import DropZone from '@/reusables/DropZone.vue'
import FilterChip from '@/reusables/FilterChip.vue'
import MediaCard from '@/reusables/MediaCard.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import ProgressBar from '@/reusables/ProgressBar.vue'
import StatCard from '@/reusables/StatCard.vue'
import { ACCEPTED_MEDIA, SUPPORTED_FILE_TYPES } from '@/utils/mediaTypes'

const router = useRouter()
const { items, visible, counts, filter, isLoading, error, prepend, removeMany } = useMedia()
const { jobs, active, isUploading, add, dismiss, clearFinished } = useMediaUpload(prepend)
const { storage } = useFleetHealth()
const { bytes, duration, dimensions } = useFormat()

// --- The figures along the top ---

const totalBytes = computed(() => items.value.reduce((sum, m) => sum + m.size_bytes, 0))
const videoSeconds = computed(() =>
  items.value.reduce((sum, m) => sum + (m.kind === 'video' ? (m.duration_seconds ?? 0) : 0), 0),
)
const storageHint = computed(() => {
  if (!storage.value) return 'Across the account'
  if (!storage.value.quota_bytes) return 'No quota set'
  const pct = Math.min(100, Math.round((storage.value.used_bytes / storage.value.quota_bytes) * 100))
  return `of ${bytes(storage.value.quota_bytes)} (${pct}%)`
})

/** The line under a tile's name: a video's resolution, a picture's, and its size either way. */
function metaFor(m: { width: number | null; height: number | null; size_bytes: number }): string {
  const size = bytes(m.size_bytes)
  return m.width && m.height ? `${dimensions(m.width, m.height)} · ${size}` : size
}

/** The header's Upload button — the drop zone's own picker, reachable without scrolling to it. */
const fileInput = ref<HTMLInputElement | null>(null)
function onPicked(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.length) add(Array.from(input.files))
  input.value = ''
}

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
    <PageTitle title="Media" subtitle="Pictures and videos your screens can play.">
      <template #actions>
        <AppButton @click="fileInput?.click()">
          <IconUpload class="size-4" aria-hidden="true" />
          Upload
        </AppButton>
      </template>
    </PageTitle>
    <input ref="fileInput" type="file" multiple class="hidden" :accept="ACCEPTED_MEDIA" @change="onPicked" />

    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <StatCard label="Files" :value="counts.all" tone="brand" :hint="`${bytes(totalBytes)} in total`" />
      <StatCard
        label="Images" :value="counts.image" :openable="counts.image > 0 && filter !== 'image'"
        hint="Shown for a set time" @open="filter = 'image'"
      />
      <StatCard
        label="Videos" :value="counts.video" :openable="counts.video > 0 && filter !== 'video'"
        :hint="counts.video ? `${duration(videoSeconds)} of video` : 'None yet'" @open="filter = 'video'"
      />
      <StatCard label="Storage" :value="storage ? bytes(storage.used_bytes) : bytes(totalBytes)" :hint="storageHint" />
    </div>

    <DropZone
      :accept="ACCEPTED_MEDIA"
      label="Drop images or videos here"
      :hint="SUPPORTED_FILE_TYPES"
      @files="add"
    />

    <!-- Upload queue. Two run at once; the rest wait. -->
    <section v-if="jobs.length" class="flex flex-col gap-2 rounded-2xl bg-canvas p-4 sm:p-5" aria-label="Uploads">
      <div class="flex items-center justify-between">
        <h2 class="text-base">{{ isUploading ? `Uploading ${active.length}…` : 'Uploads finished' }}</h2>
        <!-- Successful rows remove themselves; this only ever clears failures the user has
             already read. -->
        <AppButton v-if="!isUploading" variant="ghost" size="sm" @click="clearFinished">
          Clear
        </AppButton>
      </div>
      <div v-for="job in jobs" :key="job.id" class="rounded-xl bg-surface p-3">
        <div class="flex items-baseline justify-between gap-3">
          <p class="truncate text-sm text-ink">{{ job.name }}</p>
          <p class="shrink-0 text-[13px]" :class="job.status === 'failed' ? 'text-danger' : 'text-ink-muted'">
            {{ STATUS_LABEL[job.status] }}
          </p>
        </div>
        <ProgressBar v-if="job.status === 'uploading'" :value="job.progress" class="mt-2" />
        <p v-if="job.error" class="mt-1.5 text-[13px] text-danger">{{ job.error }}</p>
        <AppButton v-if="job.status === 'failed'" variant="ghost" size="sm" class="mt-1.5"
                   @click="dismiss(job.id)">
          Dismiss
        </AppButton>
      </div>
    </section>

    <!-- The library itself: one panel holding its filters, selection and files. -->
    <section class="flex flex-col gap-4 rounded-2xl bg-canvas p-4 sm:p-5" aria-labelledby="library-heading">
      <div class="flex flex-wrap items-center gap-2">
        <h2 id="library-heading" class="mr-2 text-lg">Library</h2>
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

      <p v-if="isLoading" class="py-10 text-center text-sm text-ink-muted">Loading…</p>

      <div v-else-if="!visible.length" class="py-12 text-center">
        <p class="text-base text-ink">Nothing here yet</p>
        <p class="mt-1 text-sm text-ink-muted">
          {{ counts.all ? 'No files of this type. Try a different filter.' : 'Upload a file, or drop one above.' }}
        </p>
      </div>

      <div v-else class="grid grid-cols-2 gap-x-3 gap-y-5 sm:grid-cols-3 lg:grid-cols-4">
        <MediaCard
          v-for="m in visible"
          :key="m.id"
          :filename="m.filename"
          :kind="m.kind"
          :thumbnail-url="m.thumbnail_url"
          :meta="metaFor(m)"
          :badge="m.kind === 'video' && m.duration_seconds != null ? duration(m.duration_seconds) : undefined"
          :selectable="selecting"
          :selected="selected.has(m.id)"
          @click="onTile(m.id)"
        />
      </div>
    </section>

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
