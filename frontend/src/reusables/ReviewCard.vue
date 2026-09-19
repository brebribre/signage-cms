<script setup lang="ts">
/**
 * One review in the list: who asked, what they changed, and the screens and playlists it
 * touches — enough to know whether to open it, never enough to decide from here. The same
 * card for a waiting review (one way in: "See the changes") and a decided one (its verdict
 * and the owner's note).
 */
import IconChevronRight from '~icons/material-symbols/chevron-right'
import IconPlaylistPlay from '~icons/material-symbols/playlist-play'
import IconTv from '~icons/material-symbols/tv-outline'

import { useFormat } from '@/hooks/useFormat'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import NamePills from '@/reusables/NamePills.vue'
import type { ReviewKind, ReviewRead, ReviewStatus } from '@/types/api'

defineProps<{ review: ReviewRead }>()
const emit = defineEmits<{ open: [] }>()
const { relativeTime } = useFormat()

const KIND_LABEL: Record<ReviewKind, string> = {
  playlist_items: 'Playlist change',
  playlist_shuffle: 'Shuffle',
  campaign_create: 'New campaign',
  campaign_update: 'Campaign change',
  campaign_delete: 'Campaign removal',
  schedule_create: 'New schedule',
  schedule_update: 'Schedule change',
  schedule_delete: 'Schedule removal',
  device_playlist: 'Screen assignment',
}

const STATUS: Record<ReviewStatus, { label: string; cls: string }> = {
  pending: { label: 'Waiting', cls: 'bg-brand-soft text-brand' },
  approved: { label: 'Approved', cls: 'bg-emerald-50 text-emerald-700' },
  rejected: { label: 'Rejected', cls: 'bg-raised text-danger' },
  withdrawn: { label: 'Withdrawn', cls: 'bg-raised text-ink-muted' },
}

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
        <dl class="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-3 gap-y-1.5">
          <dt class="text-[12px] text-ink-subtle">Screens</dt>
          <dd><NamePills :names="review.screens" :icon="IconTv" noun="screens" /></dd>
          <dt class="text-[12px] text-ink-subtle">Playlists</dt>
          <dd><NamePills :names="review.playlists" :icon="IconPlaylistPlay" noun="playlists" /></dd>
        </dl>

        <p v-if="review.note" class="text-[13px] text-ink-muted">“{{ review.note }}”</p>

        <AppButton v-if="review.status === 'pending'" variant="ghost" size="sm" class="-ml-2 self-start" @click.stop="emit('open')">
          {{ review.kind === 'playlist_items' ? 'See the changes and preview' : 'See the changes' }}
          <IconChevronRight class="size-4" aria-hidden="true" />
        </AppButton>
      </div>
    </div>
  </AppCard>
</template>
