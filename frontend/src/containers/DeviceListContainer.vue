<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { useDevices } from '@/hooks/useDevices'
import { useFormat } from '@/hooks/useFormat'
import { usePlaylists } from '@/hooks/usePlaylists'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import AppInput from '@/reusables/AppInput.vue'
import AppModal from '@/reusables/AppModal.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import StatusDot from '@/reusables/StatusDot.vue'

const router = useRouter()
const { items, isLoading, isSaving, error, claimError, connecting, claim, assignPlaylist } =
  useDevices()
const { items: playlists } = usePlaylists()
const { relativeTime } = useFormat()

const pairing = ref(false)
const form = ref({ pairing_code: '', name: '', location: '' })

async function onClaim() {
  const ok = await claim({ ...form.value })
  if (!ok) return
  // Held briefly so "connected" is actually seen — closing the instant the promise resolves
  // throws away the one piece of feedback that says the screen really started.
  if (!claimError.value) {
    await new Promise((r) => setTimeout(r, 900))
    pairing.value = false
    form.value = { pairing_code: '', name: '', location: '' }
  }
}

function onAssign(deviceId: string, e: Event) {
  const value = (e.target as HTMLSelectElement).value
  assignPlaylist(deviceId, value || null)
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
      <AppCard
        v-for="d in items"
        :key="d.id"
        interactive
        @click="router.push({ name: 'device-detail', params: { id: d.id } })"
      >
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="min-w-0">
            <p class="truncate text-base text-ink">{{ d.name || 'Unnamed screen' }}</p>
            <p class="mt-0.5 text-[13px] text-ink-muted">
              <span v-if="d.location">{{ d.location }} · </span>
              {{ d.orientation }} · last seen {{ relativeTime(d.last_seen_at) }}
            </p>
          </div>

          <div class="flex shrink-0 items-center gap-4" @click.stop>
            <StatusDot :last-seen-at="d.last_seen_at" />
            <!-- Assignable right from the list: this is the single most common thing a
                 screen row is opened for, and select→save round trips in one click here
                 instead of a full detail page visit. -->
            <select
              class="rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px]
                     text-ink focus:border-ink focus:outline-none"
              :value="d.playlist_id ?? ''"
              @change="onAssign(d.id, $event)"
            >
              <option value="">No playlist</option>
              <option v-for="p in playlists" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
        </div>
      </AppCard>
    </div>

    <AppModal v-if="pairing" title="Add a screen" @close="pairing = false">
      <form class="flex flex-col gap-3" @submit.prevent="onClaim">
        <p class="text-[13px] text-ink-muted">
          Type the code shown on the screen. Codes expire after 15 minutes.
        </p>
        <AppInput
          id="pair-code"
          v-model="form.pairing_code"
          label="Pairing code"
          placeholder="ABCDEF"
          required
          hint="Not case-sensitive"
        />
        <AppInput id="pair-name" v-model="form.name" label="Name" placeholder="Lobby" required />
        <AppInput
          id="pair-location"
          v-model="form.location"
          label="Location"
          placeholder="Ground floor"
        />
        <AppAlert v-if="claimError" tone="danger">{{ claimError }}</AppAlert>

        <!-- The handshake, shown as it happens. The claim returns instantly but the screen
             only learns about it on its next poll, so "created" alone sends people away from
             a screen that has not started yet. -->
        <div
          v-if="isSaving && connecting"
          class="flex items-center gap-2 rounded-lg bg-surface px-3 py-2 text-[13px] text-ink-muted"
        >
          <span
            class="size-2 shrink-0 animate-pulse rounded-full bg-ink"
            aria-hidden="true"
          />
          Waiting for {{ connecting.name }} to connect…
        </div>
        <div
          v-else-if="connecting?.connected"
          class="rounded-lg bg-surface px-3 py-2 text-[13px] text-ink"
        >
          {{ connecting.name }} connected.
        </div>

        <div class="mt-1 flex justify-end gap-2">
          <AppButton variant="secondary" size="sm" type="button" @click="pairing = false">
            Cancel
          </AppButton>
          <AppButton size="sm" type="submit" :loading="isSaving">
            {{ isSaving && connecting ? 'Connecting…' : 'Add screen' }}
          </AppButton>
        </div>
      </form>
    </AppModal>
  </div>
</template>
