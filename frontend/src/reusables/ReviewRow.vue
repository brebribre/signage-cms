<script setup lang="ts">
/**
 * One review as a line in a list: what kind of change (its icon), what it does, who sent it and
 * when, the screens it reaches, and where it stands. A way in, never a place to decide —
 * approving without having looked at the change is the one thing the list must not make easy,
 * so the whole line is a link to the review's own page and there are no buttons on it.
 *
 * Lines sit inside a card, separated by hairlines (the caller's `divide-y`), so a day's changes
 * read as one group — the Reviews page groups them by day, the Overview lists the waiting ones.
 */
import IconChevronRight from '~icons/material-symbols/chevron-right'

import { useFormat } from '@/hooks/useFormat'
import NamePills from '@/reusables/NamePills.vue'
import type { ReviewRead } from '@/types/api'
import {
  REVIEW_KIND_ICON as KIND_ICON,
  REVIEW_KIND_LABEL as KIND_LABEL,
  REVIEW_KIND_REMOVES as REMOVES,
  REVIEW_STATUS as STATUS,
} from '@/utils/reviewLabels'

withDefaults(defineProps<{
  review: ReviewRead
  /** Off where the list is already one status (a Waiting tab), so every line doesn't repeat it. */
  showStatus?: boolean
}>(), { showStatus: true })
const { relativeTime } = useFormat()
</script>

<template>
  <router-link
    :to="{ name: 'review-detail', params: { id: review.id } }"
    class="group flex items-start gap-3 px-4 py-3.5 transition-colors duration-150 hover:bg-surface
           focus-visible:bg-surface focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand-bright"
  >
    <span
      class="flex size-10 shrink-0 items-center justify-center rounded-xl"
      :class="REMOVES.has(review.kind) ? 'bg-raised text-danger' : 'bg-brand-soft text-brand'"
      aria-hidden="true"
    >
      <component :is="KIND_ICON[review.kind]" class="size-5" />
    </span>

    <div class="flex min-w-0 flex-1 flex-col gap-1.5">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <p class="text-sm font-medium text-ink [overflow-wrap:anywhere]">{{ review.summary }}</p>
          <p class="mt-0.5 text-[13px] text-ink-muted">
            {{ KIND_LABEL[review.kind] }} · {{ review.requested_by_name }} · {{ relativeTime(review.created_at) }}
          </p>
        </div>
        <span class="flex shrink-0 items-center gap-1">
          <span v-if="showStatus" class="rounded-full px-2.5 py-0.5 text-[12px]" :class="STATUS[review.status].cls">
            {{ STATUS[review.status].label }}
          </span>
          <IconChevronRight class="size-5 text-ink-subtle transition-transform duration-150 group-hover:translate-x-0.5" aria-hidden="true" />
        </span>
      </div>

      <NamePills v-if="review.screens.length" :names="review.screens" noun="screens" />
      <p v-if="review.note" class="text-[13px] text-ink-muted">“{{ review.note }}”</p>
    </div>
  </router-link>
</template>
