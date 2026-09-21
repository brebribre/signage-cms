<script setup lang="ts">
/**
 * Software updates: every uploaded player build, what's live, and rolling a build out — to the
 * whole fleet (a rollout) or to chosen screens (a per-screen pin, which wins over the fleet for
 * those screens). Either now or at a set time. Owner-only.
 */
import { computed, ref } from 'vue'

import { useDevices } from '@/hooks/useDevices'
import { useFormat } from '@/hooks/useFormat'
import { useNowPlaying } from '@/hooks/useNowPlaying'
import { usePlayerRollouts } from '@/hooks/usePlayerRollouts'
import { usePlaylists } from '@/hooks/usePlaylists'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppModal from '@/reusables/AppModal.vue'
import DeviceCard from '@/reusables/DeviceCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import type { DeviceRead, PlayerReleaseRead, PlayerRolloutRead } from '@/types/api'
import { describeUpdate } from '@/utils/updateStatus'

const { releases, rollouts, isLoading, isSaving, error, schedule, cancel, pinDevices, cancelPin } = usePlayerRollouts()
const { items: allDevices, resolved, refresh: refreshDevices } = useDevices()
/** Only Android screens install player builds — a web screen reloads onto the newest web
 *  player deploy instead, so it has no place in version counts or the screen picker. */
const devices = computed(() => allDevices.value.filter((d) => d.platform !== 'web'))
const { items: playlists } = usePlaylists()
const { nowPlaying } = useNowPlaying(resolved, playlists)
const { bytes, date, dateTime } = useFormat()

const activeRollout = computed(() => rollouts.value.find((r) => r.is_active) ?? null)
/** Screens with an update of their own still waiting to install, under way, or just failed —
 *  otherwise invisible from here. A fleet rollout's failures show up here too: the screen reports
 *  them the same way, pin or no pin, and "3 screens still on 1.1.9" says nothing about why. */
const pendingPins = computed(() =>
  devices.value.filter((d) => {
    const v = describeUpdate(d)
    return !!v && v.kind !== 'installed'
  }),
)
/** One line per screen: what's happening to it, from its own reports. */
function updateLine(d: DeviceRead): string {
  const v = describeUpdate(d)
  if (!v) return ''
  switch (v.kind) {
    case 'downloading': return `Downloading${v.percent !== null ? ` · ${v.percent}%` : ''}`
    case 'installing': return 'Installing'
    case 'stalled': return 'No news from the screen'
    case 'failed': return `Failed: ${d.update_detail ?? 'no reason given'}`
    default: return pinWhen(d)
  }
}

/** How many screens report running each version — what's actually out there, rather than what
 *  the fleet rollout says should be. A screen that has never reported a version isn't counted. */
const screensByVersion = computed(() => {
  const counts = new Map<string, number>()
  for (const d of devices.value) {
    if (d.app_version) counts.set(d.app_version, (counts.get(d.app_version) ?? 0) + 1)
  }
  return counts
})
function screensOn(version: string): string {
  const n = screensByVersion.value.get(version) ?? 0
  return n ? `${n} screen${n === 1 ? '' : 's'}` : 'No screens'
}

const isFuture = (iso: string | null) => !!iso && new Date(iso).getTime() > Date.now()
const isUpcoming = (r: PlayerRolloutRead) => !r.is_active && isFuture(r.scheduled_at)

function pinWhen(d: DeviceRead): string {
  return isFuture(d.forced_update_at) ? dateTime(d.forced_update_at!) : 'Right away'
}

/** What the picker shows per screen: what it runs, and anything already on its way to it. */
function versionLabel(d: DeviceRead): string {
  const running = d.app_version ?? 'Version unknown'
  if (!d.forced_update_version) return running
  return `${running} → ${d.forced_update_version}${isFuture(d.forced_update_at) ? ` · ${dateTime(d.forced_update_at!)}` : ''}`
}

// --- Rolling out ---

const scheduling = ref<PlayerReleaseRead | null>(null)
const target = ref<'all' | 'screens'>('all')
const pickedIds = ref<string[]>([])
const timing = ref<'now' | 'later'>('now')
const localDateTime = ref('')
const scheduleError = ref<string | null>(null)

function openSchedule(release: PlayerReleaseRead) {
  scheduling.value = release
  target.value = 'all'
  pickedIds.value = []
  timing.value = 'now'
  localDateTime.value = ''
  scheduleError.value = null
}

function togglePick(id: string) {
  const at = pickedIds.value.indexOf(id)
  at >= 0 ? pickedIds.value.splice(at, 1) : pickedIds.value.push(id)
}
const allPicked = computed(() => devices.value.length > 0 && pickedIds.value.length === devices.value.length)
function toggleAllPicked() {
  pickedIds.value = allPicked.value ? [] : devices.value.map((d) => d.id)
}

const confirmLabel = computed(() => {
  if (target.value === 'all') return timing.value === 'now' ? 'Roll out now' : 'Schedule'
  const n = pickedIds.value.length
  const verb = timing.value === 'now' ? 'Update' : 'Schedule'
  return n ? `${verb} ${n} screen${n === 1 ? '' : 's'}` : `${verb} screens`
})

async function onConfirmSchedule() {
  if (!scheduling.value) return
  scheduleError.value = null
  let scheduledAt: string | null = null
  if (timing.value === 'later') {
    if (!localDateTime.value) {
      scheduleError.value = 'Pick a date and time.'
      return
    }
    // A bare "YYYY-MM-DDTHH:MM" from <input type="datetime-local"> has no offset — the Date
    // constructor reads it as this browser's local time, which is what the person meant.
    const asDate = new Date(localDateTime.value)
    if (asDate.getTime() <= Date.now()) {
      scheduleError.value = 'Pick a time in the future, or choose Now.'
      return
    }
    scheduledAt = asDate.toISOString()
  }

  if (target.value === 'screens') {
    if (!pickedIds.value.length) {
      scheduleError.value = 'Pick at least one screen.'
      return
    }
    const ok = await pinDevices(scheduling.value.version, pickedIds.value, scheduledAt)
    await refreshDevices()
    if (ok) scheduling.value = null
    return
  }

  if (await schedule(scheduling.value.version, scheduledAt)) scheduling.value = null
}

const confirmingCancel = ref<PlayerRolloutRead | null>(null)
async function onCancel() {
  if (confirmingCancel.value && (await cancel(confirmingCancel.value.id))) confirmingCancel.value = null
}

const confirmingPin = ref<DeviceRead | null>(null)
async function onCancelPin() {
  if (confirmingPin.value && (await cancelPin(confirmingPin.value.id))) {
    confirmingPin.value = null
    await refreshDevices()
  }
}

const PILL = 'rounded-full border px-3 py-1 text-[13px] transition-colors duration-200'
const pillClass = (on: boolean) => (on ? 'border-ink bg-ink text-ink-inverse' : 'border-line-strong text-ink-muted hover:bg-raised')
const LIST = 'divide-y divide-line overflow-hidden rounded-xl bg-surface'
const ROW = 'flex items-center gap-3 px-4 py-2.5'
</script>

<template>
  <div class="flex flex-col gap-8">
    <div v-if="activeRollout" class="flex flex-col gap-1">
      <p class="text-[13px] text-ink-muted">
        Live: <span class="text-ink tabular-nums">{{ activeRollout.version }}</span>
        · since {{ dateTime(activeRollout.scheduled_at) }}
      </p>
    </div>

    <AppAlert v-if="error && !scheduling" tone="danger">{{ error }}</AppAlert>
    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>

    <template v-else>
      <section class="flex flex-col gap-2">
        <h2 class="text-lg">Releases</h2>
        <EmptyState
          v-if="!releases.length"
          title="No builds uploaded yet"
          description="Upload one with publish_player_apk.py."
        />
        <ul v-else :class="LIST">
          <li v-for="r in releases" :key="r.version" :class="ROW">
            <span class="w-14 shrink-0 text-sm tabular-nums text-ink">{{ r.version }}</span>
            <span
              class="w-24 shrink-0 text-[13px] tabular-nums"
              :class="screensByVersion.get(r.version) ? 'text-ink' : 'text-ink-subtle'"
            >
              {{ screensOn(r.version) }}
            </span>
            <span class="min-w-0 flex-1 truncate text-[13px] text-ink-muted">
              {{ date(r.uploaded_at) }} · {{ bytes(r.size_bytes) }}
            </span>
            <AppButton size="sm" variant="secondary" @click="openSchedule(r)">Roll out</AppButton>
          </li>
        </ul>
      </section>

      <section v-if="pendingPins.length" class="flex flex-col gap-2">
        <h2 class="text-lg">Pending on screens</h2>
        <ul :class="LIST">
          <li v-for="d in pendingPins" :key="d.id" :class="ROW">
            <span class="min-w-0 flex-1 truncate text-sm text-ink">{{ d.name || 'Unnamed screen' }}</span>
            <span class="shrink-0 text-[13px] tabular-nums text-ink-muted">
              {{ d.app_version ?? '?' }} → {{ d.forced_update_version ?? d.update_version }}
            </span>
            <span
              class="hidden w-56 shrink-0 truncate text-right text-[13px] sm:inline"
              :class="describeUpdate(d)?.tone === 'danger' ? 'text-danger' : 'text-ink-subtle'"
              :title="updateLine(d)"
            >
              {{ updateLine(d) }}
            </span>
            <AppButton variant="ghost" size="sm" @click="confirmingPin = d">
              {{ describeUpdate(d)?.kind === 'failed' ? 'Dismiss' : 'Cancel' }}
            </AppButton>
          </li>
        </ul>
      </section>

      <section class="flex flex-col gap-2">
        <h2 class="text-lg">History</h2>
        <EmptyState v-if="!rollouts.length" title="No rollouts yet" />
        <ul v-else :class="LIST">
          <li v-for="r in rollouts" :key="r.id" :class="ROW">
            <span class="w-14 shrink-0 text-sm tabular-nums text-ink">{{ r.version }}</span>
            <span class="w-20 shrink-0">
              <span
                class="rounded-full px-2 py-0.5 text-[11px]"
                :class="r.is_active ? 'bg-ink text-ink-inverse' : isUpcoming(r) ? 'border border-ink text-ink' : 'text-ink-subtle'"
              >
                {{ r.is_active ? 'Live' : isUpcoming(r) ? 'Scheduled' : 'Past' }}
              </span>
            </span>
            <span class="min-w-0 flex-1 truncate text-[13px] text-ink-muted">{{ dateTime(r.scheduled_at) }}</span>
            <AppButton v-if="isUpcoming(r)" size="sm" variant="ghost" @click="confirmingCancel = r">Cancel</AppButton>
          </li>
        </ul>
      </section>
    </template>

    <AppModal v-if="scheduling" :title="`Roll out ${scheduling.version}`" size="xl" @close="scheduling = null">
      <form class="flex flex-col gap-4" @submit.prevent="onConfirmSchedule">
        <div class="flex flex-wrap items-end gap-x-8 gap-y-3">
          <div class="flex flex-col gap-1.5">
            <span class="text-[13px] text-ink-muted">Screens</span>
            <div class="flex gap-2">
              <button type="button" :class="[PILL, pillClass(target === 'all')]" @click="target = 'all'">All screens</button>
              <button type="button" :class="[PILL, pillClass(target === 'screens')]" @click="target = 'screens'">Choose screens</button>
            </div>
          </div>
          <div class="flex flex-col gap-1.5">
            <span class="text-[13px] text-ink-muted">When</span>
            <div class="flex gap-2">
              <button type="button" :class="[PILL, pillClass(timing === 'now')]" @click="timing = 'now'">Now</button>
              <button type="button" :class="[PILL, pillClass(timing === 'later')]" @click="timing = 'later'">Later</button>
            </div>
          </div>
          <input
            v-if="timing === 'later'"
            v-model="localDateTime"
            type="datetime-local"
            aria-label="Date and time"
            class="h-9 rounded-lg border border-line-strong bg-canvas px-3 text-sm text-ink focus:border-ink focus:outline-none"
          />
        </div>

        <template v-if="target === 'screens'">
          <div class="flex items-center justify-between">
            <button type="button" class="text-[13px] text-ink-muted hover:text-ink" @click="toggleAllPicked">
              {{ allPicked ? 'Clear' : 'Select all' }}
            </button>
            <span class="text-[13px] tabular-nums text-ink-muted">{{ pickedIds.length }} / {{ devices.length }}</span>
          </div>
          <p v-if="!devices.length" class="text-sm text-ink-muted">No screens yet.</p>
          <div v-else class="flex max-h-[45vh] flex-col gap-2 overflow-y-auto">
            <DeviceCard
              v-for="d in devices"
              :key="d.id"
              :device="d"
              :playing="nowPlaying(d.id).text"
              :via="nowPlaying(d.id).via"
              :version-label="versionLabel(d)"
              selectable
              :selected="pickedIds.includes(d.id)"
              @click="togglePick(d.id)"
            />
          </div>
        </template>

        <AppAlert v-if="scheduleError || error" tone="danger">{{ scheduleError || error }}</AppAlert>

        <ModalActions>
          <AppButton variant="secondary" size="sm" type="button" @click="scheduling = null">Cancel</AppButton>
          <AppButton size="sm" type="submit" :loading="isSaving">{{ confirmLabel }}</AppButton>
        </ModalActions>
      </form>
    </AppModal>

    <AppModal v-if="confirmingCancel" title="Cancel this rollout?" @close="confirmingCancel = null">
      <p class="text-sm text-ink-muted">
        {{ confirmingCancel.version }} won't take over at {{ dateTime(confirmingCancel.scheduled_at) }}.
      </p>
      <ModalActions>
        <AppButton variant="secondary" size="sm" @click="confirmingCancel = null">Keep it</AppButton>
        <AppButton variant="danger" size="sm" :loading="isSaving" @click="onCancel">Cancel rollout</AppButton>
      </ModalActions>
    </AppModal>

    <AppModal v-if="confirmingPin" title="Cancel this update?" @close="confirmingPin = null">
      <p class="text-sm text-ink-muted">
        {{ confirmingPin.name }} won't install {{ confirmingPin.forced_update_version }} and follows the fleet again.
      </p>
      <ModalActions>
        <AppButton variant="secondary" size="sm" @click="confirmingPin = null">Keep it</AppButton>
        <AppButton variant="danger" size="sm" :loading="isSaving" @click="onCancelPin">Cancel update</AppButton>
      </ModalActions>
    </AppModal>
  </div>
</template>
