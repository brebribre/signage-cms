<script setup lang="ts">
/**
 * One screen's software update, live: pick a build and push it, then watch it actually happen —
 * waiting, downloading with a percentage, installing, done — or read why it didn't, and retry.
 * Owner-only (the parent decides), same boundary as the rest of player build management.
 *
 * Everything shown comes from `describeUpdate` (utils/updateStatus.ts), fed by the screen's own
 * reports; the parent hook keeps polling while something is in flight. This component only
 * decides how to lay the story out and which buttons make sense at each point.
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'

import IconCheckCircle from '~icons/material-symbols/check-circle-outline'
import IconError from '~icons/material-symbols/error-outline'

import { usePlayerRolloutApi } from '@/api/usePlayerRolloutApi'
import { useFormat } from '@/hooks/useFormat'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import AppModal from '@/reusables/AppModal.vue'
import AppSpinner from '@/reusables/AppSpinner.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import ProgressBar from '@/reusables/ProgressBar.vue'
import type { DeviceRead, PlayerReleaseRead } from '@/types/api'
import { describeUpdate } from '@/utils/updateStatus'

const props = defineProps<{
  device: DeviceRead
  isSaving: boolean
  /** Pins a build to this screen. Also what "Retry now" calls — re-issuing the same version is
   *  a fresh request the screen acts on at once, cooldown or not. */
  setUpdate: (version: string) => Promise<boolean>
  /** Cancels a pending pin, or dismisses what the screen last reported. */
  cancelUpdate: () => Promise<boolean>
}>()

const { bytes } = useFormat()

const releaseApi = usePlayerRolloutApi()
const releases = ref<PlayerReleaseRead[]>([])
onMounted(() => {
  releaseApi.releases().then((r) => { releases.value = r }).catch(() => {})
})

// "last report 4s ago" has to keep counting between polls, and the stalled threshold is a
// function of time, not of data arriving — so the view is recomputed on a ticking clock.
const now = ref(Date.now())
const tick = setInterval(() => { now.value = Date.now() }, 1_000)
onUnmounted(() => clearInterval(tick))

const view = computed(() => describeUpdate(props.device, now.value))

/** "7.8 of 18.3 MB" under the bar, when the build's size is known; the percentage itself is
 *  already in the detail line. */
const sizeOf = (version: string) => releases.value.find((r) => r.version === version)?.size_bytes ?? null
const progressLine = computed(() => {
  const v = view.value
  if (!v || v.percent === null) return null
  const size = sizeOf(v.version)
  return size ? `${bytes(Math.round((size * v.percent) / 100))} of ${bytes(size)}` : null
})

const pickedVersion = ref('')
const confirmingUpdate = ref(false)
const confirmingCancel = ref(false)

async function onConfirmUpdate() {
  if (!pickedVersion.value) return
  if (await props.setUpdate(pickedVersion.value)) {
    confirmingUpdate.value = false
    pickedVersion.value = ''
  }
}

async function onRetry() {
  const v = view.value
  if (v) await props.setUpdate(v.version)
}

async function onCancel() {
  if (await props.cancelUpdate()) confirmingCancel.value = false
}

/** Dismissing a finished update needs no confirmation — nothing is lost. Cancelling one that
 *  hasn't happened yet does, since the screen will then stay on what it runs. */
function onCancelClick() {
  const v = view.value
  if (!v) return
  if (v.kind === 'installed' || v.kind === 'failed') void props.cancelUpdate()
  else confirmingCancel.value = true
}

/** The picker stays available once an update has finished either way — but not while one is
 *  in flight, where a second instruction would only race the first, and not on a Basic screen,
 *  which can't act on it: there, the note above points at the releases page instead. */
const showPicker = computed(() => props.device.device_owner !== false && (!view.value || !view.value.busy))

/** Where a person installs a build by hand — the docs' list of every release. Shown for a
 *  Basic screen, which can't install one itself. */
const RELEASES_DOCS_URL = 'https://docs.paskall.co.id/player-releases/'

/** "1.3.7" > "1.3.5", numerically per part; a suffix like "-emu" is ignored. Unparseable
 *  versions (a web screen's "web-1.0.0") compare as older than nothing. */
function versionParts(v: string | null): number[] | null {
  if (!v) return null
  const m = /^(\d+(?:\.\d+)*)/.exec(v)
  return m ? m[1].split('.').map(Number) : null
}
function isNewer(a: string, b: string | null): boolean {
  const pa = versionParts(a); const pb = versionParts(b)
  if (!pa || !pb) return false
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const d = (pa[i] ?? 0) - (pb[i] ?? 0)
    if (d !== 0) return d > 0
  }
  return false
}

/** The newest uploaded build, when it is newer than what this screen runs — the "there is
 *  something to update to" signal, whether or not the screen can do it by itself. */
const newerRelease = computed(() => {
  const newest = releases.value.reduce<PlayerReleaseRead | null>(
    (best, r) => (!best || isNewer(r.version, best.version) ? r : best), null,
  )
  return newest && isNewer(newest.version, props.device.app_version) ? newest : null
})
</script>

<template>
  <div>
    <h2 class="text-sm text-ink">Software update</h2>
    <p class="mt-0.5 text-[13px] text-ink-muted">
      Push a specific build to just this screen, independent of the fleet rollout.
    </p>
    <p v-if="device.device_owner === false" class="mt-2 rounded-lg bg-raised px-3 py-2 text-[13px] text-ink-muted">
      This screen is set up as <b class="text-ink">Basic</b>: the player isn't Device Owner, so it can't
      install a build by itself. To update it, download the build from the
      <a :href="RELEASES_DOCS_URL" target="_blank" rel="noopener" class="text-brand underline-offset-2 hover:underline">Player Releases</a>
      page on the screen and open it there.
    </p>
    <!-- Something newer exists than what the screen runs — said plainly, with the version, so
         nobody has to compare numbers in the picker. -->
    <p
      v-if="newerRelease"
      class="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg bg-brand-soft px-3 py-2 text-[13px] text-ink"
    >
      <span class="rounded-full bg-brand px-2 py-0.5 text-[11px] font-medium tracking-wider text-ink-inverse uppercase">New release</span>
      <span>
        <b>{{ newerRelease.version }}</b> is available; this screen runs {{ device.app_version ?? 'an unknown version' }}.
      </span>
    </p>

    <AppCard v-if="view || showPicker" class="mt-3 flex flex-col gap-4">
      <div v-if="view" class="flex items-start gap-3" aria-live="polite">
        <span class="mt-0.5 flex size-6 shrink-0 items-center justify-center">
          <AppSpinner v-if="view.busy" size="md" class="text-ink" :label="view.title" />
          <IconCheckCircle v-else-if="view.tone === 'success'" class="size-6 text-emerald-700" aria-hidden="true" />
          <IconError v-else-if="view.tone === 'danger'" class="size-6 text-danger" aria-hidden="true" />
          <span v-else class="size-2 rounded-full bg-ink-subtle" aria-hidden="true" />
        </span>

        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
            <p
              class="text-sm"
              :class="view.tone === 'danger' ? 'text-danger' : view.tone === 'success' ? 'text-emerald-700' : 'text-ink'"
            >
              {{ view.title }}
            </p>
            <div class="flex shrink-0 items-center gap-2">
              <AppButton v-if="view.canRetry" size="sm" :loading="isSaving" @click="onRetry">
                Retry now
              </AppButton>
              <AppButton
                v-if="view.canCancel"
                variant="ghost"
                size="sm"
                :disabled="isSaving"
                @click="onCancelClick"
              >
                {{ view.kind === 'installed' || view.kind === 'failed' ? 'Dismiss' : 'Cancel' }}
              </AppButton>
            </div>
          </div>

          <template v-if="view.kind === 'downloading' || (view.kind === 'stalled' && view.percent !== null)">
            <ProgressBar
              class="mt-2"
              :value="(view.percent ?? 0) / 100"
              :indeterminate="view.percent === null"
            />
            <p v-if="progressLine" class="mt-1.5 text-[13px] tabular-nums text-ink-muted">
              {{ progressLine }}
            </p>
          </template>
          <ProgressBar v-else-if="view.kind === 'installing'" class="mt-2" indeterminate />

          <p class="mt-1.5 text-[13px] text-ink-muted">{{ view.detail }}</p>
        </div>
      </div>

      <div v-if="showPicker" :class="view ? 'border-t border-line pt-4' : ''">
        <div class="flex flex-wrap items-center gap-3">
          <select
            v-model="pickedVersion"
            class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm
                   text-ink focus:border-ink focus:outline-none"
            aria-label="Version to install"
          >
            <option value="" disabled>Choose a version</option>
            <option v-for="r in releases" :key="r.version" :value="r.version">
              {{ r.version }}{{ r.is_current ? ' (current fleet build)' : '' }}{{ r.version === device.app_version ? ' (installed)' : '' }}
            </option>
          </select>
          <AppButton size="sm" :disabled="!pickedVersion" @click="confirmingUpdate = true">
            Update this screen
          </AppButton>
        </div>
        <p v-if="!releases.length" class="mt-2 text-[13px] text-ink-subtle">
          No builds uploaded yet — publish one with publish_player_apk.py first.
        </p>
      </div>
    </AppCard>

    <AppModal v-if="confirmingUpdate" title="Update this screen?" @close="confirmingUpdate = false">
      <p class="text-sm text-ink-muted">
        {{ device.name }} will download and install <b>{{ pickedVersion }}</b> right away —
        within a few seconds, or on its next check-in if it can't be reached by push — regardless
        of what the rest of the fleet is running. You can
        follow it here as it happens.
      </p>
      <ModalActions>
        <AppButton variant="secondary" size="sm" @click="confirmingUpdate = false">Cancel</AppButton>
        <AppButton size="sm" :loading="isSaving" @click="onConfirmUpdate">Update</AppButton>
      </ModalActions>
    </AppModal>

    <AppModal v-if="confirmingCancel" title="Cancel this update?" @close="confirmingCancel = false">
      <p class="text-sm text-ink-muted">
        <template v-if="view?.kind === 'pending'">
          {{ device.name }} will not install {{ view.version }}. It stays on whatever it's
          currently running until the fleet rollout — or a new single-screen update — says
          otherwise.
        </template>
        <template v-else>
          The screen is already installing {{ view?.version }} and can't be told to stop —
          this only clears the update from this page. If it finishes, the screen will simply
          check in on the new build.
        </template>
      </p>
      <ModalActions>
        <AppButton variant="secondary" size="sm" @click="confirmingCancel = false">Keep it</AppButton>
        <AppButton variant="danger" size="sm" :loading="isSaving" @click="onCancel">Cancel update</AppButton>
      </ModalActions>
    </AppModal>
  </div>
</template>
