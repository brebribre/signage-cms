<script setup lang="ts">
/**
 * One review in the list: who asked, what they changed, and the screens and playlists it
 * touches — enough to know whether to open it, never enough to decide from here. The same
 * card for a waiting review (one way in: "Review") and a decided one (its verdict
 * and the owner's note).
 */
import IconChevronRight from '~icons/material-symbols/chevron-right'
import IconPlaylistPlay from '~icons/material-symbols/playlist-play'
import IconTv from '~icons/material-symbols/tv-outline'

import { useFormat } from '@/hooks/useFormat'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import NamePills from '@/reusables/NamePills.vue'
import type { ReviewRead } from '@/types/api'
import { REVIEW_KIND_LABEL as KIND_LABEL, REVIEW_STATUS as STATUS } from '@/utils/reviewLabels'

defineProps<{ review: ReviewRead }>()
const emit = defineEmits<{ open: [] }>()
const { relativeTime } = useFormat()

/** Two letters for the avatar, the way the user list does it. */
function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  const letters = parts.length >= 2 ? parts[0][0] + parts[parts.length - 1][0] : (parts[0] ?? '?').slice(0, 2)
  return letters.toUpperCase()
}
</script>

<template>
  <AppCard interactive @click="emit('open')">
    <div class="flex gap-3">
      <span
        class="flex size-9 shrink-0 items-center justify-center rounded-full bg-brand-soft text-[13px] font-medium text-brand"
        aria-hidden="true"
      >{{ initials(review.requested_by_name) }}</span>

      <div class="flex min-w-0 flex-1 flex-col gap-2">
        <div class="flex flex-wrap items-start justify-between gap-x-4 gap-y-1">
          <div class="min-w-0">
            <p class="text-sm text-ink">
              {{ review.requested_by_name }}
              <span class="text-ink-subtle"> · {{ relativeTime(review.created_at) }}</span>
            </p>
            <p class="text-[13px] text-ink-muted">{{ KIND_LABEL[review.kind] }}</p>
          </div>
          <span
            v-if="review.status !== 'pending'"
            class="shrink-0 rounded-full px-2.5 py-0.5 text-[12px]"
            :class="STATUS[review.status].cls"
            :title="review.reviewed_at ? relativeTime(review.reviewed_at) : undefined"
          >
            {{ STATUS[review.status].label }}
          </span>
        </div>

        <p class="text-base text-ink">{{ review.summary }}</p>

        <!-- Screens and playlists on their own rows, two names each and the rest counted, so
             a change to a whole venue reads the same size as a change to one screen. -->
        <dl class="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-2.5 gap-y-1.5">
          <dt class="flex" title="Screens"><IconTv class="size-4 text-ink-muted" aria-label="Screens" /></dt>
          <dd><NamePills :names="review.screens" noun="screens" /></dd>
          <dt class="flex" title="Playlists"><IconPlaylistPlay class="size-4 text-ink-muted" aria-label="Playlists" /></dt>
          <dd><NamePills :names="review.playlists" noun="playlists" /></dd>
        </dl>

        <p v-if="review.note" class="text-[13px] text-ink-muted">“{{ review.note }}”</p>

        <AppButton v-if="review.status === 'pending'" size="sm" class="self-start" @click.stop="emit('open')">
          Review
          <IconChevronRight class="size-4" aria-hidden="true" />
        </AppButton>
      </div>
    </div>
  </AppCard>
</template>
