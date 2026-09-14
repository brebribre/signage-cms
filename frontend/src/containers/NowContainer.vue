<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Ref } from 'vue'
import { useRouter } from 'vue-router'
import IconPhotoLibrary from '~icons/material-symbols/photo-library-outline'
import IconPlaylistPlay from '~icons/material-symbols/playlist-play'
import IconTv from '~icons/material-symbols/tv-outline'

import { useDevices } from '@/hooks/useDevices'
import { useFleetHealth } from '@/hooks/useFleetHealth'
import { useFormat } from '@/hooks/useFormat'
import { useMedia } from '@/hooks/useMedia'
import { useNowPlaying } from '@/hooks/useNowPlaying'
import { usePlaylists } from '@/hooks/usePlaylists'
import AppAlert from '@/reusables/AppAlert.vue'
import AppCard from '@/reusables/AppCard.vue'
import AppModal from '@/reusables/AppModal.vue'
import DeviceCard from '@/reusables/DeviceCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import FilterChip from '@/reusables/FilterChip.vue'
import OnboardingCard from '@/reusables/OnboardingCard.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import PairScreenForm from '@/reusables/PairScreenForm.vue'
import type { ClaimBody } from '@/types/api'

/**
 * Overview: the fleet at a glance — summary figures, filters, and every screen as the same card
 * the Devices list uses, so a screen reads identically wherever you meet it. See
 * UX_REDESIGN_PLAN.md §3 for where this page came from.
 */
const router = useRouter()
const {
  items: devices, resolved, isLoading: devicesLoading, error: devicesError,
  isSaving: claiming, claimError, connecting, claim,
} = useDevices()
const { devices: health, storage, offline, withErrors, isLoading: healthLoading } = useFleetHealth()
const { items: playlists, isLoading: playlistsLoading, error: playlistsError } = usePlaylists()
const { items: media, isLoading: mediaLoading, error: mediaError } = useMedia()

// --- First steps: a big prompt for whatever the account doesn't have yet ---

/** True once a list has finished its first load without failing — so a prompt never flashes
 *  before the data arrives, and a failed load isn't mistaken for "you have none". */
function loadedOk(loading: Ref<boolean>, error: Ref<string | null>) {
  const ok = ref(false)
  watch(loading, (now, before) => {
    if (before && !now) ok.value = !error.value
  })
  return ok
}
const devicesReady = loadedOk(devicesLoading, devicesError)
const mediaReady = loadedOk(mediaLoading, mediaError)
const playlistsReady = loadedOk(playlistsLoading, playlistsError)

const needsScreen = computed(() => devicesReady.value && !devices.value.length)
const needsMedia = computed(() => mediaReady.value && !media.value.length)
const needsPlaylist = computed(() => playlistsReady.value && !playlists.value.length)

const pairing = ref(false)
async function onClaim(body: ClaimBody) {
  if (!(await claim(body))) return
  // Held briefly so "connected" is actually seen before the dialog closes.
  if (!claimError.value) {
    await new Promise((r) => setTimeout(r, 900))
    pairing.value = false
  }
}
const { nowPlaying } = useNowPlaying(resolved, playlists)
const { bytes } = useFormat()

const healthByDevice = computed(() => new Map(health.value.map((h) => [h.device_id, h])))

/** What each filter needs, joined once rather than looked up again per filter, per render. */
const rows = computed(() =>
  devices.value.map((d) => {
    const h = healthByDevice.value.get(d.id)
    return {
      device: d,
      isOffline: !h?.is_online,
      errorCount: h?.error_count_24h ?? 0,
      // "Playing default only": no schedule is currently winning for this screen — the coverage
      // gap the Campaigns list can't answer on its own.
      isDefaultOnly: !resolved.value.get(d.id)?.schedule_id,
    }
  }),
)

type Filter = 'all' | 'offline' | 'errors' | 'default'
const filter = ref<Filter>('all')

const defaultOnlyCount = computed(() => rows.value.filter((r) => r.isDefaultOnly).length)

const filtered = computed(() => {
  switch (filter.value) {
    case 'offline': return rows.value.filter((r) => r.isOffline)
    case 'errors': return rows.value.filter((r) => r.errorCount > 0)
    case 'default': return rows.value.filter((r) => r.isDefaultOnly)
    default: return rows.value
  }
})

function quotaPercent(used: number, quota: number | null): number | null {
  return quota ? Math.min(100, Math.round((used / quota) * 100)) : null
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle title="Overview" subtitle="What every screen is playing, right now, and why." />

    <AppAlert v-if="devicesError" tone="danger">{{ devicesError }}</AppAlert>

    <div v-if="needsScreen || needsMedia || needsPlaylist" class="flex flex-col gap-3">
      <OnboardingCard
        v-if="needsScreen"
        :icon="IconTv"
        title="Connect your first screen"
        description="Power on a screen and type the code it shows."
        action="Add screen"
        @action="pairing = true"
      />
      <OnboardingCard
        v-if="needsMedia"
        :icon="IconPhotoLibrary"
        title="Upload your first media"
        description="Images and videos to put on your screens."
        action="Upload media"
        @action="router.push({ name: 'media' })"
      />
      <OnboardingCard
        v-if="needsPlaylist"
        :icon="IconPlaylistPlay"
        title="Create your first playlist"
        description="Arrange media into a loop a screen can play."
        action="New playlist"
        @action="router.push({ name: 'playlists', query: { new: '1' } })"
      />
    </div>

    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <AppCard>
        <p class="text-[13px] text-ink-muted">Screens</p>
        <p class="mt-0.5 text-2xl">{{ devices.length }}</p>
      </AppCard>
      <AppCard>
        <p class="text-[13px] text-ink-muted">Offline</p>
        <p class="mt-0.5 text-2xl" :class="offline.length ? 'text-danger' : 'text-ink'">
          {{ offline.length }}
        </p>
      </AppCard>
      <AppCard>
        <p class="text-[13px] text-ink-muted">Reporting errors</p>
        <p class="mt-0.5 text-2xl" :class="withErrors.length ? 'text-danger' : 'text-ink'">
          {{ withErrors.length }}
        </p>
      </AppCard>
      <AppCard>
        <p class="text-[13px] text-ink-muted">Storage</p>
        <p class="mt-0.5 text-2xl">{{ storage ? bytes(storage.used_bytes) : '—' }}</p>
        <p v-if="storage?.quota_bytes" class="text-[13px] text-ink-muted">
          of {{ bytes(storage.quota_bytes) }}
          ({{ quotaPercent(storage.used_bytes, storage.quota_bytes) }}%)
        </p>
        <p v-else-if="storage" class="text-[13px] text-ink-subtle">no quota set</p>
      </AppCard>
    </div>

    <div class="flex flex-wrap gap-2">
      <FilterChip :active="filter === 'all'" :count="rows.length" @click="filter = 'all'">
        All
      </FilterChip>
      <FilterChip :active="filter === 'offline'" :count="offline.length" @click="filter = 'offline'">
        Offline
      </FilterChip>
      <FilterChip :active="filter === 'errors'" :count="withErrors.length" @click="filter = 'errors'">
        Errors
      </FilterChip>
      <FilterChip :active="filter === 'default'" :count="defaultOnlyCount" @click="filter = 'default'">
        Playing default only
      </FilterChip>
    </div>

    <p v-if="(devicesLoading || healthLoading) && !devices.length" class="text-sm text-ink-muted">
      Loading…
    </p>

    <EmptyState
      v-else-if="!filtered.length"
      title="Nothing here"
      :description="rows.length ? 'No screens match this filter.' : 'Pair a screen and it will appear here.'"
    />

    <!-- The Devices list's own card, so a screen reads identically on both pages. -->
    <div v-else class="flex flex-col gap-2">
      <DeviceCard
        v-for="r in filtered"
        :key="r.device.id"
        :device="r.device"
        :playing="nowPlaying(r.device.id).text"
        :via="nowPlaying(r.device.id).via"
        @click="router.push({ name: 'device-detail', params: { id: r.device.id } })"
      />
    </div>

    <AppModal v-if="pairing" title="Add a screen" @close="pairing = false">
      <PairScreenForm
        :is-saving="claiming" :claim-error="claimError" :connecting="connecting"
        @submit="onClaim" @cancel="pairing = false"
      />
    </AppModal>
  </div>
</template>
