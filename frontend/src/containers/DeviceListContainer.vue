<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useDevices } from '@/hooks/useDevices'
import { usePlaylists } from '@/hooks/usePlaylists'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppModal from '@/reusables/AppModal.vue'
import DeviceCard from '@/reusables/DeviceCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import PairScreenForm from '@/reusables/PairScreenForm.vue'
import type { ClaimBody, DeviceRead } from '@/types/api'

const router = useRouter()
const { items, resolved, isLoading, isSaving, error, claimError, connecting, claim } = useDevices()
const { items: playlists } = usePlaylists()

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

const playlistName = (playlistId: string) => playlists.value.find((p) => p.id === playlistId)?.name ?? '—'

/** What a card shows for "currently playing" — resolved server-side from this device's
 *  campaigns, same as the manifest a screen actually gets. Assigning playlists happens only
 *  in Campaigns; this is read-only. */
function nowPlaying(d: DeviceRead): { text: string; via: string | null } {
  const r = resolved.value.get(d.id)
  if (!r || !r.playlist_id) return { text: 'No playlist', via: null }
  return {
    text: playlistName(r.playlist_id),
    via: r.schedule_name ? `via “${r.schedule_name}”` : null,
  }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle title="Devices" :subtitle="`${items.length} screen${items.length === 1 ? '' : 's'}`">
      <template #actions>
        <AppButton variant="secondary" size="sm" @click="router.push({ name: 'campaigns' })">
          Campaigns
        </AppButton>
        <AppButton size="sm" @click="pairing = true">Add screen</AppButton>
      </template>
    </PageTitle>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>

    <EmptyState
      v-else-if="!items.length"
      title="No screens yet"
      description="Power on a screen — it will show a pairing code. Type that code here to add it."
    >
      <template #actions>
        <AppButton size="sm" @click="pairing = true">Add screen</AppButton>
      </template>
    </EmptyState>

    <div v-else class="flex flex-col gap-2">
      <DeviceCard
        v-for="d in items"
        :key="d.id"
        :device="d"
        :playing="nowPlaying(d).text"
        :via="nowPlaying(d).via"
        @click="router.push({ name: 'device-detail', params: { id: d.id } })"
      />
    </div>

    <AppModal v-if="pairing" title="Add a screen" @close="pairing = false">
      <PairScreenForm
        :is-saving="isSaving" :claim-error="claimError" :connecting="connecting"
        @submit="onClaim" @cancel="pairing = false"
      />
    </AppModal>
  </div>
</template>
