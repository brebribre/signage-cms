<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useDevices } from '@/hooks/useDevices'
import { useNowPlaying } from '@/hooks/useNowPlaying'
import { usePlaylists } from '@/hooks/usePlaylists'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppModal from '@/reusables/AppModal.vue'
import DeviceCard from '@/reusables/DeviceCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import PairScreenForm from '@/reusables/PairScreenForm.vue'
import type { ClaimBody } from '@/types/api'

const router = useRouter()
const { items, resolved, isLoading, isSaving, error, claimError, connecting, claim } = useDevices()
const { items: playlists } = usePlaylists()
const { nowPlaying } = useNowPlaying(resolved, playlists)

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
        :playing="nowPlaying(d.id).text"
        :via="nowPlaying(d.id).via"
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
