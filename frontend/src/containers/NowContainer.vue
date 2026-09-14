<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useCampaigns } from '@/hooks/useCampaigns'
import { useDevices } from '@/hooks/useDevices'
import { useFleetHealth } from '@/hooks/useFleetHealth'
import { useFormat } from '@/hooks/useFormat'
import { usePlaylists } from '@/hooks/usePlaylists'
import AppAlert from '@/reusables/AppAlert.vue'
import AppCard from '@/reusables/AppCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import FilterChip from '@/reusables/FilterChip.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import ResolutionChip from '@/reusables/ResolutionChip.vue'
import StatusDot from '@/reusables/StatusDot.vue'

/**
 * A new, additive view — not a replacement for Devices or Health, both of which are
 * untouched. See UX_REDESIGN_PLAN.md §3: this is the fleet-wide "what's happening right
 * now, and why" surface the redesign proposes, built alongside the current pages so it can
 * be compared directly before anything old is removed.
 */
const router = useRouter()
const { items: devices, resolved, isLoading: devicesLoading, error: devicesError } = useDevices()
const { devices: health, storage, offline, withErrors, isLoading: healthLoading } = useFleetHealth()
const { items: campaigns } = useCampaigns()
const { items: playlists } = usePlaylists()
const { bytes, relativeTime } = useFormat()

const healthByDevice = computed(() => new Map(health.value.map((h) => [h.device_id, h])))
const playlistName = (id: string | null) =>
  (id ? (playlists.value.find((p) => p.id === id)?.name ?? null) : null)
const campaignName = (id: string | null) =>
  (id ? (campaigns.value.find((c) => c.id === id)?.name ?? null) : null)

/** Everything a row needs, joined once — the alternative is five separate map lookups
 *  scattered through the template for every device, every render. */
const rows = computed(() =>
  devices.value.map((d) => {
    const resolution = resolved.value.get(d.id) ?? null
    const h = healthByDevice.value.get(d.id)
    return {
      device: d,
      resolution,
      playlistName: playlistName(resolution?.playlist_id ?? null),
      campaignName: campaignName(resolution?.campaign_id ?? null),
      campaignTo: resolution?.campaign_id
        ? { name: 'campaign-detail', params: { id: resolution.campaign_id } }
        : null,
      isOffline: !h?.is_online,
      errorCount: h?.error_count_24h ?? 0,
      // "Playing default only": no schedule is currently winning for this screen — exactly
      // the coverage gap the Campaigns list can't answer today (it shows counts of screens
      // a campaign targets, never which screens no campaign covers at all).
      isDefaultOnly: !resolution?.schedule_id,
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
    <PageTitle title="Now" subtitle="What every screen is playing, right now, and why." />

    <AppAlert v-if="devicesError" tone="danger">{{ devicesError }}</AppAlert>

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

    <ul v-else class="flex flex-col gap-2">
      <li v-for="r in filtered" :key="r.device.id">
        <AppCard interactive @click="router.push({ name: 'device-detail', params: { id: r.device.id } })">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="min-w-0 flex-1">
              <p class="truncate text-base text-ink">
                {{ r.device.name || 'Unnamed screen' }}
                <span v-if="r.device.location" class="text-[13px] font-normal text-ink-subtle">
                  · {{ r.device.location }}
                </span>
              </p>
              <ResolutionChip
                class="mt-0.5"
                :resolution="r.resolution"
                :playlist-name="r.playlistName"
                :campaign-name="r.campaignName"
                :campaign-to="r.campaignTo"
              />
              <p class="mt-0.5 text-[13px] text-ink-subtle">
                last seen {{ relativeTime(r.device.last_seen_at) }}
              </p>
            </div>
            <div class="flex shrink-0 items-center gap-4">
              <span v-if="r.errorCount" class="text-[13px] text-danger">
                {{ r.errorCount }} error{{ r.errorCount === 1 ? '' : 's' }}
              </span>
              <StatusDot :last-seen-at="r.device.last_seen_at" />
            </div>
          </div>
        </AppCard>
      </li>
    </ul>
  </div>
</template>
