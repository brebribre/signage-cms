<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import fortuLogoUrl from '@/assets/fortu-logo.png'
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
import type { DeviceRead } from '@/types/api'

const router = useRouter()
const { items, resolved, isLoading, isSaving, error, claimError, connecting, claim } = useDevices()
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

const playlistName = (playlistId: string) => playlists.value.find((p) => p.id === playlistId)?.name ?? '—'

// Every row reserves the same square footprint for its screen mock, so a portrait device
// never makes its own row taller than the landscape ones around it — only what's drawn
// inside that footprint (see screenBox) changes with orientation, letterboxed to fit.
const SLOT_PX = 88

/** The rectangle drawn inside the fixed slot: the device's actual resolution when it has
 *  reported one, else a generic ratio for its orientation, scaled to fit within `SLOT_PX`
 *  on its longer side. Clamped at both ends so one very wide or very narrow screen can't
 *  collapse to nothing — this is a shape indicator, not a pixel-accurate preview. */
function screenBox(d: DeviceRead): { width: number; height: number } {
  const ratio = d.screen_width && d.screen_height
    ? d.screen_width / d.screen_height
    : d.orientation === 'portrait' ? 9 / 16 : 16 / 9
  const clamped = Math.min(Math.max(ratio, 0.4), 2.4)
  const width = clamped >= 1 ? SLOT_PX : Math.round(SLOT_PX * clamped)
  const height = clamped >= 1 ? Math.round(SLOT_PX / clamped) : SLOT_PX
  return { width: Math.max(width, 36), height: Math.max(height, 36) }
}

/** What a row shows for "currently playing" — resolved server-side from this device's
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
      <AppCard
        v-for="d in items"
        :key="d.id"
        interactive
        @click="router.push({ name: 'device-detail', params: { id: d.id } })"
      >
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex min-w-0 items-center gap-4">
            <!-- A shape, not a pixel-accurate preview: the device's own aspect ratio and
                 orientation, so a row of screens reads at a glance like the wall it maps to.
                 The outer slot is a fixed square so every row stays the same height; the
                 bordered rectangle inside it is what actually changes shape. -->
            <div
              class="flex shrink-0 items-center justify-center"
              :style="{ width: `${SLOT_PX}px`, height: `${SLOT_PX}px` }"
            >
              <div
                class="flex items-center justify-center overflow-hidden rounded-sm
                       border-[5px] border-ink bg-canvas px-3 py-2"
                :style="{ width: `${screenBox(d).width}px`, height: `${screenBox(d).height}px` }"
              >
                <!-- The source file is a light wordmark on a transparent ground — invisible
                     on this white screen mock — so it's used as a mask and painted solid
                     black instead of drawn as-is. -->
                <span
                  class="block h-full w-full bg-ink"
                  :style="{
                    maskImage: `url(${fortuLogoUrl})`,
                    WebkitMaskImage: `url(${fortuLogoUrl})`,
                    maskRepeat: 'no-repeat',
                    WebkitMaskRepeat: 'no-repeat',
                    maskPosition: 'center',
                    WebkitMaskPosition: 'center',
                    maskSize: 'contain',
                    WebkitMaskSize: 'contain',
                  }"
                  role="img"
                  aria-label="Fortu logo"
                />
              </div>
            </div>
            <div class="min-w-0">
              <p class="truncate text-base text-ink">{{ d.name || 'Unnamed screen' }}</p>
              <p class="mt-0.5 text-[13px] text-ink-muted">
                <span v-if="d.location">{{ d.location }} · </span>
                {{ d.orientation }} · last seen {{ relativeTime(d.last_seen_at) }}
              </p>
            </div>
          </div>

          <div class="flex shrink-0 items-center gap-3">
            <!-- Read-only: what this screen plays is decided in Campaigns, not here. -->
            <div class="text-right">
              <p class="text-[13px] text-ink">{{ nowPlaying(d).text }}</p>
              <p v-if="nowPlaying(d).via" class="text-[13px] text-ink-subtle">{{ nowPlaying(d).via }}</p>
            </div>
            <StatusDot :last-seen-at="d.last_seen_at" />
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
