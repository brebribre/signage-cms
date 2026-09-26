<script setup lang="ts">
/**
 * Every campaign, as a list that answers "is it on air, where, and with what" at a glance — the
 * shape of a marketing tool's campaign list: search and status filters above, one line per
 * campaign with its status as a coloured badge, and what it reaches beside it.
 *
 * "Playing now" is the same count the Overview shows: how many of the campaign's screens it is
 * the one winning on right now, from each screen's live resolution (useDevices), so the list
 * never disagrees with what the walls are showing. Search matches the campaign's name, its
 * screens and its playlists — "which campaign is on the lobby TV?" is a search, not a scroll.
 */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import IconAdd from '~icons/material-symbols/add'
import IconChevronRight from '~icons/material-symbols/chevron-right'
import IconPlaylistPlay from '~icons/material-symbols/playlist-play'
import IconSearch from '~icons/material-symbols/search'
import IconTv from '~icons/material-symbols/tv-outline'

import { useCampaigns } from '@/hooks/useCampaigns'
import { useDevices } from '@/hooks/useDevices'
import { useFormat } from '@/hooks/useFormat'
import { usePlaylists } from '@/hooks/usePlaylists'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import FilterChip from '@/reusables/FilterChip.vue'
import ListRowSkeleton from '@/reusables/ListRowSkeleton.vue'
import NamePills from '@/reusables/NamePills.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import SkeletonList from '@/reusables/SkeletonList.vue'
import type { CampaignSummary } from '@/types/api'

const router = useRouter()
const { items, isLoading, error } = useCampaigns()
const { items: devices, resolved } = useDevices()
const { items: playlists } = usePlaylists()
const { relativeTime } = useFormat()

// --- What each campaign reaches, by name ---

const deviceName = computed(() => new Map(devices.value.map((d) => [d.id, d.name || 'Unnamed screen'])))
const playlistName = computed(() => new Map(playlists.value.map((p) => [p.id, p.name])))
const screensOf = (c: CampaignSummary) =>
  c.device_ids.map((id) => deviceName.value.get(id)).filter((n): n is string => !!n)
const playlistsOf = (c: CampaignSummary) =>
  (c.playlist_ids ?? []).map((id) => playlistName.value.get(id)).filter((n): n is string => !!n)

/** Screens each campaign is winning on right now — the Overview's count. */
const playingOn = computed(() => {
  const counts = new Map<string, number>()
  for (const r of resolved.value.values()) {
    if (r.campaign_id) counts.set(r.campaign_id, (counts.get(r.campaign_id) ?? 0) + 1)
  }
  return counts
})
const isPlaying = (c: CampaignSummary) => (playingOn.value.get(c.id) ?? 0) > 0

/** The badge: on air, idle, or — worth flagging — on no screens at all (every one it had was
 *  removed), which no schedule can fix. */
function status(c: CampaignSummary): { label: string; cls: string; dot: string } {
  if (isPlaying(c)) {
    return { label: `Playing on ${playingOn.value.get(c.id)} of ${c.device_count}`, cls: 'bg-emerald-50 text-emerald-700', dot: 'bg-emerald-600' }
  }
  if (!c.device_count) return { label: 'No screens', cls: 'bg-amber-50 text-amber-700', dot: 'bg-amber-500' }
  return { label: 'Not playing now', cls: 'bg-raised text-ink-muted', dot: 'bg-ink-subtle' }
}

// --- Search and filter ---

type Filter = 'all' | 'playing' | 'idle'
const filter = ref<Filter>('all')
const query = ref('')

const playingCount = computed(() => items.value.filter(isPlaying).length)

const visible = computed(() => {
  const q = query.value.trim().toLowerCase()
  return items.value
    .filter((c) => (filter.value === 'playing' ? isPlaying(c) : filter.value === 'idle' ? !isPlaying(c) : true))
    .filter((c) => !q || [c.name, ...screensOf(c), ...playlistsOf(c)].some((v) => v.toLowerCase().includes(q)))
    // On air first, then the most recently changed: the ones worth a look lead.
    .sort((a, b) => Number(isPlaying(b)) - Number(isPlaying(a)) || b.updated_at.localeCompare(a.updated_at))
})

function open(c: CampaignSummary) {
  router.push({ name: 'campaign-detail', params: { id: c.id } })
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle
      title="Campaigns"
      :subtitle="items.length
        ? `${items.length} campaign${items.length === 1 ? '' : 's'} · ${playingCount} playing now`
        : 'No campaigns yet'"
    >
      <template #actions>
        <AppButton size="sm" @click="router.push({ name: 'deploy' })">
          <IconAdd class="size-4" aria-hidden="true" />
          New campaign
        </AppButton>
      </template>
    </PageTitle>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <SkeletonList v-if="isLoading && !items.length" label="Loading campaigns">
      <ListRowSkeleton />
    </SkeletonList>

    <EmptyState
      v-else-if="!items.length"
      title="No campaigns yet"
      description="A campaign assigns one or more playlists, each on its own schedule, to
                    every screen you pick — the only place playlist assignment happens."
    >
      <template #actions>
        <AppButton size="sm" @click="router.push({ name: 'deploy' })">
          <IconAdd class="size-4" aria-hidden="true" />
          New campaign
        </AppButton>
      </template>
    </EmptyState>

    <template v-else>
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
        <label class="relative block sm:w-72">
          <IconSearch class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-subtle" aria-hidden="true" />
          <input
            v-model="query"
            type="search"
            placeholder="Search campaigns"
            aria-label="Search campaigns by name, screen or playlist"
            class="w-full rounded-lg border border-line-strong bg-canvas py-2 pr-3 pl-9 text-sm text-ink
                   focus:border-brand focus:outline-none"
          />
        </label>
        <div class="flex flex-wrap gap-2" role="group" aria-label="Filter campaigns">
          <FilterChip :active="filter === 'all'" :count="items.length" :aria-pressed="filter === 'all'" @click="filter = 'all'">All</FilterChip>
          <FilterChip :active="filter === 'playing'" :count="playingCount" :aria-pressed="filter === 'playing'" @click="filter = 'playing'">Playing now</FilterChip>
          <FilterChip :active="filter === 'idle'" :count="items.length - playingCount" :aria-pressed="filter === 'idle'" @click="filter = 'idle'">Not playing</FilterChip>
        </div>
      </div>

      <EmptyState
        v-if="!visible.length"
        title="No campaigns match"
        :description="query ? `No campaign's name, screens or playlists match “${query.trim()}”.` : 'Nothing in this filter right now.'"
      >
        <template #actions>
          <AppButton variant="secondary" size="sm" @click="query = ''; filter = 'all'">Show all campaigns</AppButton>
        </template>
      </EmptyState>

      <!-- One card, a line per campaign: columns on a wide screen, stacked on a phone. -->
      <div v-else class="overflow-hidden rounded-2xl bg-canvas">
        <div class="hidden grid-cols-[minmax(0,1.4fr)_9.5rem_minmax(0,1fr)_minmax(0,1fr)_1.25rem] gap-4 bg-surface px-4 py-3
                    text-[12px] text-ink-muted lg:grid" aria-hidden="true">
          <span>Campaign</span><span>Status</span><span>Screens</span><span>Playlists</span><span />
        </div>
        <ul class="divide-y divide-line lg:border-t lg:border-line">
          <li v-for="c in visible" :key="c.id">
            <button
              type="button"
              class="group grid w-full grid-cols-[minmax(0,1fr)_auto] items-start gap-x-4 gap-y-2 px-4 py-3.5 text-left
                     transition-colors duration-150 hover:bg-surface focus-visible:bg-surface focus-visible:outline-2
                     focus-visible:-outline-offset-2 focus-visible:outline-brand-bright
                     lg:grid-cols-[minmax(0,1.4fr)_9.5rem_minmax(0,1fr)_minmax(0,1fr)_1.25rem] lg:items-center"
              @click="open(c)"
            >
              <!-- Name, and when it last changed -->
              <span class="min-w-0">
                <span class="block truncate text-sm font-medium text-ink">{{ c.name }}</span>
                <span class="mt-0.5 block text-[12px] text-ink-muted">
                  {{ c.rule_count }} time slot{{ c.rule_count === 1 ? '' : 's' }} · updated {{ relativeTime(c.updated_at) }}
                </span>
              </span>

              <!-- Status: on a phone it sits top right, beside the name -->
              <span class="flex items-center justify-end gap-1 lg:justify-start">
                <span
                  class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[12px] whitespace-nowrap tabular-nums"
                  :class="status(c).cls"
                >
                  <span class="size-1.5 rounded-full" :class="status(c).dot" aria-hidden="true" />
                  {{ status(c).label }}
                </span>
                <IconChevronRight class="size-5 text-ink-subtle lg:hidden" aria-hidden="true" />
              </span>

              <!-- What it reaches: screens and playlists, labelled by icon on a phone -->
              <span class="col-span-2 flex min-w-0 items-center gap-2 lg:col-span-1">
                <IconTv class="size-4 shrink-0 text-ink-subtle lg:hidden" aria-label="Screens" />
                <NamePills :names="screensOf(c)" noun="screens" />
              </span>
              <span class="col-span-2 flex min-w-0 items-center gap-2 lg:col-span-1">
                <IconPlaylistPlay class="size-4 shrink-0 text-ink-subtle lg:hidden" aria-label="Playlists" />
                <NamePills :names="playlistsOf(c)" noun="playlists" />
              </span>

              <IconChevronRight
                class="hidden size-5 text-ink-subtle transition-transform duration-150 group-hover:translate-x-0.5 lg:block"
                aria-hidden="true"
              />
            </button>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>
