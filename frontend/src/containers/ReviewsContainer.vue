<script setup lang="ts">
/**
 * Reviews: a manager's screen-changing saves, waiting for the owner.
 *
 * The owner sees the account's queue and decides; a manager sees what they sent and how it
 * went. One page for both, because the question is the same from either side — "what is
 * waiting, and what happened to it".
 *
 * Filter chips by status, with counts, and the list under them grouped by the day each change was sent,
 * newest first — an approvals inbox. It opens on Waiting whenever anything is waiting, since that
 * is the part asking for someone. A line is a way in, not a place to decide: Approve, Reject and
 * Withdraw live on the review's own page, after the change has been seen (ReviewRow).
 */
import { computed, onMounted, ref, watch } from 'vue'

import { useAuth } from '@/hooks/useAuth'
import { useReviews } from '@/hooks/useReviews'
import AppAlert from '@/reusables/AppAlert.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import FilterChip from '@/reusables/FilterChip.vue'
import ListRowSkeleton from '@/reusables/ListRowSkeleton.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import ReviewRow from '@/reusables/ReviewRow.vue'
import SkeletonList from '@/reusables/SkeletonList.vue'
import type { ReviewRead, ReviewStatus } from '@/types/api'

const { isOwner } = useAuth()
const { items, pending, isLoading, error, refresh } = useReviews()

// --- Which status ---

type Filter = ReviewStatus | 'all'
const filter = ref<Filter>('pending')
const count = (s: ReviewStatus) => items.value.filter((r) => r.status === s).length
/** Chips, not tabs: five tabs with counts don't fit a phone, and the rest of the CMS filters its
 *  lists (Media, Screens) with these. A status nothing is in isn't offered — except Waiting,
 *  which is always there to say "nothing is waiting", and the one already chosen. */
const chips = computed(() =>
  [
    { value: 'all' as Filter, label: 'All', count: items.value.length },
    { value: 'pending' as Filter, label: 'Waiting', count: pending.value.length },
    { value: 'approved' as Filter, label: 'Approved', count: count('approved') },
    { value: 'rejected' as Filter, label: 'Rejected', count: count('rejected') },
    { value: 'withdrawn' as Filter, label: 'Withdrawn', count: count('withdrawn') },
  ].filter((c) => c.count > 0 || c.value === 'pending' || c.value === 'all' || c.value === filter.value),
)

/** Once, after the first load: nothing waiting means there is nothing to land on under Waiting,
 *  so the page opens on everything instead. */
const settled = ref(false)
watch(isLoading, (loading) => {
  if (loading || settled.value) return
  settled.value = true
  if (!pending.value.length && items.value.length) filter.value = 'all'
})

// --- Grouped by the day each was sent ---

function dayKey(iso: string): string {
  const d = new Date(iso)
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`
}
function dayLabel(iso: string): string {
  const today = new Date()
  const yesterday = new Date(Date.now() - 86_400_000)
  if (dayKey(iso) === dayKey(today.toISOString())) return 'Today'
  if (dayKey(iso) === dayKey(yesterday.toISOString())) return 'Yesterday'
  return new Date(iso).toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'short' })
    + (new Date(iso).getFullYear() === today.getFullYear() ? '' : ` ${new Date(iso).getFullYear()}`)
}

const groups = computed(() => {
  const shown = items.value
    .filter((r) => filter.value === 'all' || r.status === filter.value)
    .sort((a, b) => b.created_at.localeCompare(a.created_at))
  const out: { key: string; label: string; reviews: ReviewRead[] }[] = []
  for (const r of shown) {
    const key = dayKey(r.created_at)
    const last = out[out.length - 1]
    if (last?.key === key) last.reviews.push(r)
    else out.push({ key, label: dayLabel(r.created_at), reviews: [r] })
  }
  return out
})

/** What an empty tab says — each status has its own reason to be empty. */
const emptyText = computed(() => {
  switch (filter.value) {
    case 'pending':
      return isOwner.value ? 'Nothing is waiting for you.' : 'Nothing of yours is waiting.'
    case 'approved':
      return 'Nothing approved yet.'
    case 'rejected':
      return 'Nothing rejected.'
    case 'withdrawn':
      return 'Nothing withdrawn.'
    default:
      return 'No reviews yet.'
  }
})

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

    <SkeletonList v-if="isLoading && !items.length" label="Loading reviews">
      <ListRowSkeleton />
    </SkeletonList>

    <EmptyState
      v-else-if="!items.length"
      title="Nothing to review"
      :description="isOwner
        ? 'When a manager saves something that would change a screen — a playlist that is playing, a campaign, a schedule — it waits here for you.'
        : 'When you save something that would change a screen, it waits here for the owner. Everything else saves straight away.'"
    />

    <template v-else>
      <!-- One line that scrolls sideways on a narrow phone rather than wrapping. -->
      <div class="-mx-4 flex gap-2 overflow-x-auto px-4 [scrollbar-width:none] sm:mx-0 sm:px-0 [&::-webkit-scrollbar]:hidden" role="group" aria-label="Filter reviews">
        <FilterChip
          v-for="c in chips"
          :key="c.value"
          class="shrink-0 whitespace-nowrap"
          :active="filter === c.value"
          :count="c.count"
          :aria-pressed="filter === c.value"
          @click="filter = c.value"
        >{{ c.label }}</FilterChip>
      </div>

      <p v-if="!groups.length" class="rounded-2xl bg-canvas px-4 py-10 text-center text-sm text-ink-muted">
        {{ emptyText }}
      </p>

      <section v-for="g in groups" :key="g.key" class="flex flex-col gap-2" :aria-label="g.label">
        <h2 class="flex items-center gap-2 px-1 text-[12px] font-medium tracking-wider text-ink-subtle uppercase">
          {{ g.label }}
          <span class="font-normal tabular-nums normal-case tracking-normal">· {{ g.reviews.length }}</span>
        </h2>
        <ul class="divide-y divide-line overflow-hidden rounded-2xl bg-canvas">
          <li v-for="r in g.reviews" :key="r.id"><ReviewRow :review="r" :show-status="filter === 'all'" /></li>
        </ul>
      </section>
    </template>
  </div>
</template>
