<script setup lang="ts">
/**
 * Reviews: a manager's screen-changing saves, waiting for the owner.
 *
 * The owner sees the account's queue and decides; a manager sees what they sent and how it
 * went. One page for both, because the question is the same from either side — "what is
 * waiting, and what happened to it" — only the buttons differ.
 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import IconChevronRight from '~icons/material-symbols/chevron-right'
import IconTv from '~icons/material-symbols/tv-outline'

import { useAuth } from '@/hooks/useAuth'
import { useFormat } from '@/hooks/useFormat'
import { useReviews } from '@/hooks/useReviews'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import ListRowSkeleton from '@/reusables/ListRowSkeleton.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import SkeletonList from '@/reusables/SkeletonList.vue'
import type { ReviewKind, ReviewRead, ReviewStatus } from '@/types/api'

const router = useRouter()
const { isOwner } = useAuth()
function open(r: ReviewRead) {
  router.push({ name: 'review-detail', params: { id: r.id } })
}
const { relativeTime } = useFormat()
const { pending, decided, isLoading, error, refresh } = useReviews()

onMounted(refresh)

const KIND_LABEL: Record<ReviewKind, string> = {
  playlist_items: 'Playlist',
  playlist_shuffle: 'Playlist',
  campaign_create: 'New campaign',
  campaign_update: 'Campaign',
  campaign_delete: 'Delete campaign',
  schedule_create: 'Schedule',
  schedule_update: 'Schedule',
  schedule_delete: 'Schedule',
  device_playlist: 'Screen',
}

const STATUS: Record<ReviewStatus, { label: string; cls: string }> = {
  pending: { label: 'Waiting', cls: 'bg-brand-soft text-brand' },
  approved: { label: 'Approved', cls: 'bg-emerald-50 text-emerald-700' },
  rejected: { label: 'Rejected', cls: 'bg-raised text-danger' },
  withdrawn: { label: 'Withdrawn', cls: 'bg-raised text-ink-muted' },
}

</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle
      title="Reviews"
      :subtitle="isOwner
        ? `${pending.length} waiting for you`
        : `${pending.length} of yours waiting for the owner`"
    />

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>

    <SkeletonList v-if="isLoading && !pending.length && !decided.length" label="Loading reviews">
      <ListRowSkeleton />
    </SkeletonList>

    <EmptyState
      v-else-if="!pending.length && !decided.length"
      title="Nothing to review"
      :description="isOwner
        ? 'When a manager saves something that would change a screen — a playlist that is playing, a campaign, a schedule — it waits here for you.'
        : 'When you save something that would change a screen, it waits here for the owner. Everything else saves straight away.'"
    />

    <template v-else>
      <section v-if="pending.length" class="flex flex-col gap-2">
        <h2 class="text-sm text-ink-muted">Waiting</h2>
        <!-- A card is a way in, not a place to decide: approving without having looked at the
             change is the one thing this page must not make easy. The review's own page shows
             the change and carries Approve, Reject and Withdraw. -->
        <AppCard v-for="r in pending" :key="r.id" interactive @click="open(r)">
          <div class="flex flex-col gap-3">
            <div class="min-w-0">
              <p class="text-[13px] text-ink-subtle">
                {{ KIND_LABEL[r.kind] }} · {{ r.requested_by_name }} · {{ relativeTime(r.created_at) }}
              </p>
              <p class="mt-0.5 text-base text-ink">{{ r.summary }}</p>
              <ul v-if="r.screens.length" class="mt-2 flex flex-wrap gap-1.5">
                <li
                  v-for="name in r.screens" :key="name"
                  class="flex items-center gap-1 rounded-full bg-raised px-2.5 py-0.5 text-[12px] text-ink"
                >
                  <IconTv class="size-3.5 text-ink-muted" aria-hidden="true" />{{ name }}
                </li>
              </ul>
            </div>
            <AppButton variant="ghost" size="sm" class="-ml-2 self-start" @click.stop="open(r)">
              {{ r.kind === 'playlist_items' ? 'See the changes and preview' : 'See the changes' }}
              <IconChevronRight class="size-4" aria-hidden="true" />
            </AppButton>
          </div>
        </AppCard>
      </section>

      <section v-if="decided.length" class="flex flex-col gap-2">
        <h2 class="text-sm text-ink-muted">Decided</h2>
        <AppCard v-for="r in decided" :key="r.id" interactive @click="open(r)">
          <div class="flex flex-wrap items-start justify-between gap-x-6 gap-y-2">
            <div class="min-w-0 flex-1">
              <p class="text-[13px] text-ink-subtle">
                {{ KIND_LABEL[r.kind] }} · {{ r.requested_by_name }} · {{ relativeTime(r.created_at) }}
              </p>
              <p class="mt-0.5 text-sm text-ink">{{ r.summary }}</p>
              <p v-if="r.note" class="mt-1 text-[13px] text-ink-muted">“{{ r.note }}”</p>
            </div>
            <div class="flex shrink-0 items-center gap-1">
              <span
                class="rounded-full px-2.5 py-0.5 text-[12px]"
                :class="STATUS[r.status].cls"
                :title="r.reviewed_at ? relativeTime(r.reviewed_at) : undefined"
              >
                {{ STATUS[r.status].label }}
              </span>
              <IconChevronRight class="size-5 text-ink-subtle" aria-hidden="true" />
            </div>
          </div>
        </AppCard>
      </section>
    </template>

  </div>
</template>
