<script setup lang="ts">
/**
 * Reviews: a manager's screen-changing saves, waiting for the owner.
 *
 * The owner sees the account's queue and decides; a manager sees what they sent and how it
 * went. One page for both, because the question is the same from either side — "what is
 * waiting, and what happened to it". A card is a way in, not a place to decide: approving
 * without having looked at the change is the one thing this page must not make easy, so
 * Approve, Reject and Withdraw live on the review's own page.
 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import { useReviews } from '@/hooks/useReviews'
import AppAlert from '@/reusables/AppAlert.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import ListRowSkeleton from '@/reusables/ListRowSkeleton.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import ReviewCard from '@/reusables/ReviewCard.vue'
import SkeletonList from '@/reusables/SkeletonList.vue'
import type { ReviewRead } from '@/types/api'

const router = useRouter()
const { isOwner } = useAuth()
const { pending, decided, isLoading, error, refresh } = useReviews()

function open(r: ReviewRead) {
  router.push({ name: 'review-detail', params: { id: r.id } })
}

onMounted(refresh)
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
        <ReviewCard v-for="r in pending" :key="r.id" :review="r" @open="open(r)" />
      </section>

      <section v-if="decided.length" class="flex flex-col gap-2">
        <h2 class="text-sm text-ink-muted">Decided</h2>
        <ReviewCard v-for="r in decided" :key="r.id" :review="r" @open="open(r)" />
      </section>
    </template>
  </div>
</template>
