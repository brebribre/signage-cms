<script setup lang="ts">
/**
 * One upload's name, what it is doing right now, and its bar — the same everywhere a file is being
 * uploaded (scene editor, Add media, adding to a playlist).
 *
 * Every step says so. The bar only measures the file's transfer; before it (reading the file) and
 * after it (the server confirming the upload) the bar slides instead of sitting still, and a
 * finished upload says "Added" rather than lingering as a full bar that looks stuck.
 */
import { computed } from 'vue'
import IconCheck from '~icons/material-symbols/check'

import ProgressBar from '@/reusables/ProgressBar.vue'
import type { UploadJob } from '@/hooks/useMediaUpload'

const props = withDefaults(defineProps<{ job: UploadJob; doneLabel?: string }>(), { doneLabel: 'Added' })

/** The transfer has sent every byte but storage hasn't answered yet: that wait belongs with
 *  "Finishing", not a full bar standing still. */
const settling = computed(() =>
  props.job.status === 'finishing' || (props.job.status === 'uploading' && props.job.progress >= 1),
)

const label = computed(() => {
  if (settling.value) return 'Finishing…'
  switch (props.job.status) {
    case 'queued': return 'Waiting…'
    case 'probing': return 'Preparing…'
    case 'uploading': return `Uploading ${Math.round(props.job.progress * 100)}%`
    case 'finishing': return 'Finishing…'
    case 'done': return props.doneLabel
    default: return ''
  }
})
</script>

<template>
  <div class="min-w-0" aria-live="polite">
    <div class="flex items-baseline justify-between gap-2">
      <p class="min-w-0 truncate text-[12px] text-ink" :title="job.name">{{ job.name }}</p>
      <p
        v-if="job.status !== 'failed'"
        class="inline-flex shrink-0 items-center gap-0.5 text-[11px] tabular-nums"
        :class="job.status === 'done' ? 'text-brand' : 'text-ink-muted'"
      >
        <IconCheck v-if="job.status === 'done'" class="size-3.5" aria-hidden="true" />
        {{ label }}
      </p>
    </div>
    <p v-if="job.status === 'failed'" class="mt-0.5 text-[11px] text-danger" :title="job.error ?? undefined">
      {{ job.error }}
    </p>
    <ProgressBar
      v-else
      class="mt-1"
      :value="job.status === 'done' ? 1 : job.progress"
      :indeterminate="job.status === 'probing' || settling"
    />
  </div>
</template>
