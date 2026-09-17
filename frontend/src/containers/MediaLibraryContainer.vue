<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useMedia } from '@/hooks/useMedia'
import { useMediaUpload } from '@/hooks/useMediaUpload'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import DropZone from '@/reusables/DropZone.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import FilterChip from '@/reusables/FilterChip.vue'
import MediaCard from '@/reusables/MediaCard.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import ProgressBar from '@/reusables/ProgressBar.vue'
import { ACCEPTED_MEDIA, SUPPORTED_FILE_TYPES } from '@/utils/mediaTypes'

const router = useRouter()
const { visible, counts, filter, isLoading, error, prepend } = useMedia()
const { jobs, active, isUploading, add, dismiss, clearFinished } = useMediaUpload(prepend)

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
      <div v-for="job in jobs" :key="job.id" class="rounded-lg bg-surface p-3">
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
    </div>

    <div class="flex items-center gap-2">
      <FilterChip :active="filter === 'all'" :count="counts.all" @click="filter = 'all'">All</FilterChip>
      <FilterChip :active="filter === 'image'" :count="counts.image" @click="filter = 'image'">Images</FilterChip>
      <FilterChip :active="filter === 'video'" :count="counts.video" @click="filter = 'video'">Videos</FilterChip>
    </div>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>

    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>

    <EmptyState
      v-else-if="!visible.length"
      title="Nothing here yet"
      :description="counts.all
        ? 'No files of this type. Try a different filter.'
        : 'Drop a file above to add it to the library.'"
    />

    <div v-else class="grid grid-cols-2 gap-0.5 sm:grid-cols-3 lg:grid-cols-4">
      <MediaCard
        v-for="m in visible"
        :key="m.id"
        :filename="m.filename"
        :kind="m.kind"
        :thumbnail-url="m.thumbnail_url"
        @click="router.push({ name: 'media-detail', params: { id: m.id } })"
      />
    </div>
  </div>
</template>
