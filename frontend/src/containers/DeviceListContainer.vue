<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import IconAdd from '~icons/material-symbols/add'
import IconSearch from '~icons/material-symbols/search'

import { useDevices } from '@/hooks/useDevices'
import { useFleetHealth } from '@/hooks/useFleetHealth'
import { useNowPlaying } from '@/hooks/useNowPlaying'
import { usePlaylists } from '@/hooks/usePlaylists'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppModal from '@/reusables/AppModal.vue'
import DeviceCard from '@/reusables/DeviceCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import FilterChip from '@/reusables/FilterChip.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import PairScreenForm from '@/reusables/PairScreenForm.vue'
import DeviceCardSkeleton from '@/reusables/DeviceCardSkeleton.vue'
import SkeletonList from '@/reusables/SkeletonList.vue'
import type { ClaimBody } from '@/types/api'

const router = useRouter()
const { items, resolved, isLoading, isSaving, error, claimError, connecting, claim } = useDevices()
const { items: playlists } = usePlaylists()
const { nowPlaying } = useNowPlaying(resolved, playlists)
// Online/offline comes from the same fleet health Overview uses, so the two pages always agree.
const { devices: health } = useFleetHealth()

// --- Filter and search ---

type Filter = 'all' | 'online' | 'offline'
const filter = ref<Filter>('all')
const query = ref('')

const onlineIds = computed(() => new Set(health.value.filter((h) => h.is_online).map((h) => h.device_id)))
const onlineCount = computed(() => items.value.filter((d) => onlineIds.value.has(d.id)).length)
const offlineCount = computed(() => items.value.length - onlineCount.value)

/** Search matches a screen's name or location — what you'd call it, or where it is. */
const visible = computed(() => {
  const q = query.value.trim().toLowerCase()
  return items.value.filter((d) => {
    const online = onlineIds.value.has(d.id)
    if (filter.value === 'online' && !online) return false
    if (filter.value === 'offline' && online) return false
    return !q || d.name.toLowerCase().includes(q) || d.location.toLowerCase().includes(q)
  })
})

const pairing = ref(false)

async function onClaim(body: ClaimBody) {
  const ok = await claim(body)
  if (!ok) return
  // Held briefly so "connected" is actually seen — closing the instant the promise resolves
  // throws away the one piece of feedback that says the screen really started.
  if (!claimError.value) {
    await new Promise((r) => setTimeout(r, 900))
    pairing.value = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle title="Devices" :subtitle="`${items.length} screen${items.length === 1 ? '' : 's'}`">
      <template #actions>
        <AppButton size="sm" @click="pairing = true">
          <IconAdd class="size-4" aria-hidden="true" />
          Add screen
        </AppButton>
      </template>
    </PageTitle>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <SkeletonList v-if="isLoading" label="Loading screens" :count="3">
      <DeviceCardSkeleton />
    </SkeletonList>

    <EmptyState
      v-else-if="!items.length"
      title="No screens yet"
      description="Power on a screen — it will show a pairing code. Type that code here to add it."
    >
      <template #actions>
        <AppButton size="sm" @click="pairing = true">
          <IconAdd class="size-4" aria-hidden="true" />
          Add screen
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
          placeholder="Search screens"
          aria-label="Search screens by name or location"
          class="w-full rounded-lg border border-line-strong bg-canvas py-2 pr-3 pl-9 text-sm text-ink
                 focus:border-brand focus:outline-none"
        />
      </label>
      <div class="flex flex-wrap gap-2" role="group" aria-label="Filter screens">
        <FilterChip :active="filter === 'all'" :count="items.length" @click="filter = 'all'">All</FilterChip>
        <FilterChip :active="filter === 'online'" :count="onlineCount" @click="filter = 'online'">Online</FilterChip>
        <FilterChip :active="filter === 'offline'" :count="offlineCount" @click="filter = 'offline'">Offline</FilterChip>
      </div>
    </div>

    <EmptyState
      v-if="!visible.length"
      title="No screens match"
      :description="query ? 'Try a different name or location, or clear the search.' : 'No screens are in this state right now.'"
    />

    <div v-else class="flex flex-col gap-2">
      <DeviceCard
        v-for="d in visible"
        :key="d.id"
        :device="d"
        :playing="nowPlaying(d.id).text"
        :via="nowPlaying(d.id).via"
        @click="router.push({ name: 'device-detail', params: { id: d.id } })"
      />
    </div>
    </template>

    <AppModal v-if="pairing" title="Add a screen" @close="pairing = false">
      <PairScreenForm
        :is-saving="isSaving" :claim-error="claimError" :connecting="connecting"
        @submit="onClaim" @cancel="pairing = false"
      />
    </AppModal>
  </div>
</template>
