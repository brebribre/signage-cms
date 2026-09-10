<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
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
import type { DeviceRead } from '@/types/api'

const router = useRouter()
const {
  items, isLoading, isSaving, error, claimError, connecting,
  claim, assignPlaylist, bulkAssignPlaylist,
} = useDevices()
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

// The playlist picker changes what a physical screen shows within moments — too consequential
// to fire the instant a `<select>` changes, with nothing on the row to say it happened. A
// pick is held here as a draft until this row's own "Send" is clicked, which is when it
// actually reaches the device; savingId/sentId are what draw the loading spinner and the
// checkmark that follow.
const draftPlaylist = reactive<Record<string, string>>({})
const savingId = ref<string | null>(null)
const sentId = ref<string | null>(null)

function playlistValue(d: DeviceRead): string {
  return draftPlaylist[d.id] ?? (d.playlist_id ?? '')
}

function isDirty(d: DeviceRead): boolean {
  return playlistValue(d) !== (d.playlist_id ?? '')
}

function onPick(deviceId: string, e: Event) {
  draftPlaylist[deviceId] = (e.target as HTMLSelectElement).value
  sentId.value = null
}

async function onSend(d: DeviceRead) {
  savingId.value = d.id
  const ok = await assignPlaylist(d.id, draftPlaylist[d.id] || null)
  savingId.value = null
  if (ok) {
    delete draftPlaylist[d.id]
    sentId.value = d.id
    setTimeout(() => { if (sentId.value === d.id) sentId.value = null }, 2500)
  }
}

// Bulk mode: apply one playlist to many screens instead of visiting each row. Kept as a
// separate mode rather than layered onto the per-row draft above — the two pickers would
// otherwise fight over what a selected row is "about to" show.
const selecting = ref(false)
const selectedIds = ref<Set<string>>(new Set())
const bulkPlaylistId = ref('')
const bulkApplying = ref(false)
const bulkResult = ref<{ skippedCount: number } | null>(null)

const allSelected = computed(
  () => items.value.length > 0 && selectedIds.value.size === items.value.length
)

function toggleSelecting() {
  selecting.value = !selecting.value
  if (!selecting.value) {
    selectedIds.value = new Set()
    bulkPlaylistId.value = ''
    bulkResult.value = null
  }
}

function toggleSelected(id: string) {
  const next = new Set(selectedIds.value)
  next.has(id) ? next.delete(id) : next.add(id)
  selectedIds.value = next
}

function toggleSelectAll() {
  selectedIds.value = allSelected.value ? new Set() : new Set(items.value.map((d) => d.id))
}

async function onBulkApply() {
  bulkApplying.value = true
  bulkResult.value = null
  const { ok, skippedIds } = await bulkAssignPlaylist(
    Array.from(selectedIds.value), bulkPlaylistId.value || null
  )
  bulkApplying.value = false
  if (!ok) return
  bulkResult.value = { skippedCount: skippedIds.length }
  // Only the screens that took the change stay meaningfully "selected" — drop the rest so
  // a retry (if any) is aimed at just what actually failed.
  selectedIds.value = new Set(skippedIds)
  bulkPlaylistId.value = ''
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle title="Devices" :subtitle="`${items.length} screen${items.length === 1 ? '' : 's'}`">
      <template #actions>
        <AppButton v-if="items.length" size="sm" variant="secondary" @click="toggleSelecting">
          {{ selecting ? 'Cancel' : 'Select screens' }}
        </AppButton>
        <AppButton size="sm" @click="pairing = true">Add screen</AppButton>
      </template>
    </PageTitle>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>

    <!-- Bulk playlist assignment: pick a playlist once, apply it to every checked screen in
         one request instead of visiting each row's own picker. -->
    <div
      v-if="selecting"
      class="flex flex-wrap items-center gap-3 rounded-lg bg-surface px-3 py-2.5"
    >
      <label class="flex cursor-pointer items-center gap-2 text-[13px] text-ink-muted">
        <input
          type="checkbox" class="size-4 accent-ink" :checked="allSelected"
          @change="toggleSelectAll"
        />
        Select all
      </label>
      <span class="text-[13px] text-ink-muted">{{ selectedIds.size }} selected</span>
      <select
        class="rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px]
               text-ink focus:border-ink focus:outline-none"
        v-model="bulkPlaylistId"
      >
        <option value="">No playlist</option>
        <option v-for="p in playlists" :key="p.id" :value="p.id">{{ p.name }}</option>
      </select>
      <AppButton
        size="sm" :disabled="!selectedIds.size" :loading="bulkApplying"
        @click="onBulkApply"
      >
        Apply to {{ selectedIds.size }} screen{{ selectedIds.size === 1 ? '' : 's' }}
      </AppButton>
      <span v-if="bulkResult" class="text-[13px]" :class="bulkResult.skippedCount ? 'text-danger' : 'text-ink-muted'">
        <template v-if="bulkResult.skippedCount">
          Applied — {{ bulkResult.skippedCount }} screen{{ bulkResult.skippedCount === 1 ? '' : 's' }} couldn't be updated
        </template>
        <template v-else>Applied to every selected screen</template>
      </span>
    </div>

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
        @click="selecting ? toggleSelected(d.id) : router.push({ name: 'device-detail', params: { id: d.id } })"
      >
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex min-w-0 items-center gap-3">
            <input
              v-if="selecting"
              type="checkbox" class="size-4 shrink-0 accent-ink"
              :checked="selectedIds.has(d.id)"
              @click.stop="toggleSelected(d.id)"
            />
            <div class="min-w-0">
              <p class="truncate text-base text-ink">{{ d.name || 'Unnamed screen' }}</p>
              <p class="mt-0.5 text-[13px] text-ink-muted">
                <span v-if="d.location">{{ d.location }} · </span>
                {{ d.orientation }} · last seen {{ relativeTime(d.last_seen_at) }}
              </p>
            </div>
          </div>

          <div v-if="!selecting" class="flex shrink-0 items-center gap-2" @click.stop>
            <StatusDot :last-seen-at="d.last_seen_at" />
            <!-- Assignable right from the list: this is the single most common thing a
                 screen row is opened for. But picking a playlist only drafts it — it does
                 not reach the screen until "Send" is clicked, so nobody mistakes a dropdown
                 for something that changes nothing. -->
            <select
              class="rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px]
                     text-ink focus:border-ink focus:outline-none"
              :value="playlistValue(d)"
              @change="onPick(d.id, $event)"
            >
              <option value="">No playlist</option>
              <option v-for="p in playlists" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
            <AppButton
              v-if="isDirty(d)"
              size="sm"
              :loading="savingId === d.id"
              @click="onSend(d)"
            >
              Send
            </AppButton>
            <svg
              v-else-if="sentId === d.id"
              viewBox="0 0 16 16" class="size-4 shrink-0 text-ink-muted" fill="none"
              aria-hidden="true"
            >
              <circle cx="8" cy="8" r="7" class="stroke-current" stroke-width="1.5" />
              <path
                d="M5 8.2l2 2 4-4.4" class="stroke-current" stroke-width="1.5"
                stroke-linecap="round" stroke-linejoin="round"
              />
            </svg>
          </div>
          <StatusDot v-else :last-seen-at="d.last_seen_at" />
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
