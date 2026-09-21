<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import DeviceActivityContainer from '@/containers/DeviceActivityContainer.vue'
import DeviceNowPlayingContainer from '@/containers/DeviceNowPlayingContainer.vue'
import DeviceSettingsContainer from '@/containers/DeviceSettingsContainer.vue'
import DeviceUpdateContainer from '@/containers/DeviceUpdateContainer.vue'
import { useAuth } from '@/hooks/useAuth'
import { useDeviceDetail } from '@/hooks/useDeviceDetail'
import { useFormat } from '@/hooks/useFormat'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import AppInput from '@/reusables/AppInput.vue'
import AppModal from '@/reusables/AppModal.vue'
import ConnectAnimation from '@/reusables/ConnectAnimation.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import AppTabs from '@/reusables/AppTabs.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import StatusDot from '@/reusables/StatusDot.vue'
import { zoneOptions as zoneChoices } from '@/utils/timezones'

const route = useRoute()
const router = useRouter()
const id = String(route.params.id)

const {
  device, isLoading, isSaving, error, saveError, saveSucceeded, probeState, disconnectState,
  save, disconnect, probe, setForcedUpdate, cancelForcedUpdate,
} = useDeviceDetail(id)
const { bytes, dimensions, relativeTime, date } = useFormat()
const { isOwner } = useAuth()

const confirmingDisconnect = ref(false)

/** The handshake, as the dialog shows it — the pairing animation run the other way. */
const handshake = computed<'disconnecting' | 'disconnected' | 'failed' | null>(() => {
  switch (disconnectState.value) {
    case 'disconnecting': return 'disconnecting'
    case 'disconnected': case 'removed': return 'disconnected'
    case 'failed': return 'failed'
    default: return null
  }
})

const TABS = [
  { value: 'manage', label: 'Manage' },
  { value: 'settings', label: 'Settings' },
  { value: 'activity', label: 'Errors & logs' },
] as const
const tab = ref<(typeof TABS)[number]['value']>('manage')

// Everything below is a draft the user is composing — nothing here reaches the device until
// "Save changes" is clicked. Re-seeded whenever the confirmed device state changes, so a
// background refresh (or a save just landing) doesn't leave the form disagreeing with what
// the device actually has.
const form = reactive({
  name: '',
  location: '',
  timezone: 'UTC',
})

watch(device, (d) => {
  if (!d) return
  form.name = d.name
  form.location = d.location
  form.timezone = d.timezone
}, { immediate: true })

const isDirty = computed(() => {
  const d = device.value
  if (!d) return false
  return form.name !== d.name
    || form.location !== d.location
    || form.timezone !== d.timezone
})

/** The device's own zone always appears, even if it isn't in the common list. */
const zoneOptions = computed(() => zoneChoices(device.value?.timezone))

/**
 * One request carrying every field the user touched — a dropdown that looks as small as
 * "pick a playlist" is really "change what this screen shows in the next few seconds", and
 * it deserves the same explicit save and confirmation as everything else here rather than
 * firing the moment it's clicked.
 */
async function onSave() {
  const d = device.value
  if (!d) return
  await save({
    name: form.name,
    location: form.location,
    timezone: form.timezone,
  })
}

async function onDisconnect() {
  if (!(await disconnect())) return
  // Held so the outcome is actually seen — the screen resetting is the one piece of feedback
  // that says it really let go; a screen that never answered gets a moment longer to read why.
  await new Promise((r) => setTimeout(r, disconnectState.value === 'removed' ? 2_500 : 1_200))
  router.push({ name: 'devices' })
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <AppButton variant="ghost" size="sm" class="self-start" @click="router.push({ name: 'devices' })">
      ← Screens
    </AppButton>

    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>
    <AppAlert v-else-if="error" tone="danger">{{ error }}</AppAlert>

    <template v-else-if="device">
      <PageTitle :title="device.name || 'Unnamed screen'">
        <template #actions>
          <AppButton variant="secondary" size="sm" @click="router.push({ name: 'live-device', params: { id } })">
            Live control
          </AppButton>
          <AppButton variant="danger" size="sm" @click="confirmingDisconnect = true">Disconnect</AppButton>
        </template>
      </PageTitle>

      <AppAlert v-if="saveError" tone="danger">{{ saveError }}</AppAlert>

      <AppCard>
        <dl class="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
          <div>
            <dt class="text-[13px] text-ink-muted">Status</dt>
            <dd class="mt-0.5 flex items-center gap-2">
              <StatusDot :last-seen-at="device.last_seen_at" />
              <button
                type="button"
                class="text-[13px] underline underline-offset-2 disabled:opacity-50"
                :class="probeState === 'no-response' ? 'text-danger' : 'text-ink'"
                :disabled="probeState === 'probing'"
                @click="probe"
              >
                {{
                  probeState === 'probing' ? 'Probing…'
                  : probeState === 'online' ? 'Online'
                  : probeState === 'no-response' ? 'No response'
                  : 'Probe'
                }}
              </button>
            </dd>
          </div>
          <div>
            <dt class="text-[13px] text-ink-muted">Last seen</dt>
            <dd class="text-sm text-ink">{{ relativeTime(device.last_seen_at) }}</dd>
          </div>
          <div>
            <dt class="text-[13px] text-ink-muted">Paired</dt>
            <dd class="text-sm text-ink">{{ device.paired_at ? date(device.paired_at) : 'Not paired' }}</dd>
          </div>
          <div>
            <dt class="text-[13px] text-ink-muted">Resolution</dt>
            <dd class="text-sm text-ink">{{ dimensions(device.screen_width, device.screen_height) }}</dd>
          </div>
          <div>
            <dt class="text-[13px] text-ink-muted">Player</dt>
            <dd class="text-sm text-ink">{{ device.platform === 'web' ? 'Web browser' : 'Android' }}</dd>
          </div>
          <div>
            <dt class="text-[13px] text-ink-muted">App version</dt>
            <dd class="text-sm text-ink">{{ device.app_version ?? '—' }}</dd>
          </div>
          <!-- Managed or basic: whether the box gave the player Device Owner access, which is
               what silent updates, display switch-off and the kiosk lock all need. -->
          <div v-if="device.platform !== 'web'">
            <dt class="text-[13px] text-ink-muted">Setup</dt>
            <dd
              class="text-sm text-ink"
              :title="device.device_owner === true
                ? 'The player is Device Owner: it installs updates by itself, switches the display off on schedule, and keeps other apps out.'
                : device.device_owner === false
                  ? 'The player is not Device Owner: it plays content, but updates need a person at the screen and “off” is a black screen.'
                  : 'Not reported yet — the screen has to check in on a player that reports it.'"
            >
              {{ device.device_owner === true ? 'Managed' : device.device_owner === false ? 'Basic' : '—' }}
            </dd>
          </div>
          <!-- Playback health, from the last heartbeat — "is this box coping?" in numbers. -->
          <div v-if="device.playback_reported_at">
            <dt class="text-[13px] text-ink-muted">Playback</dt>
            <dd
              class="text-sm"
              :class="(device.playback_dropped_frames ?? 0) > 0 ? 'text-danger' : 'text-ink'"
              :title="device.playback_decoder ?? undefined"
            >
              {{ device.playback_dropped_frames ?? 0 }} dropped frame{{ device.playback_dropped_frames === 1 ? '' : 's' }}
              <span class="text-ink-subtle">since last check-in</span>
              <span v-if="device.playback_decoder" class="block truncate text-[13px] text-ink-muted">
                {{ device.playback_decoder }}
              </span>
            </dd>
          </div>
          <div v-if="device.download_bytes_per_second">
            <dt class="text-[13px] text-ink-muted">Download speed</dt>
            <dd class="text-sm text-ink">{{ bytes(device.download_bytes_per_second) }}/s <span class="text-ink-subtle">last file</span></dd>
          </div>
        </dl>
      </AppCard>

      <AppTabs :items="TABS" v-model="tab" />

      <template v-if="tab === 'manage'">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <AppInput id="dev-name" v-model="form.name" label="Name" />
          <AppInput id="dev-location" v-model="form.location" label="Location" />

          <div class="flex flex-col gap-1.5">
            <label class="text-[13px] text-ink-muted">Timezone</label>
            <select
              class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm text-ink
                     focus:border-ink focus:outline-none"
              v-model="form.timezone"
            >
              <option v-for="z in zoneOptions" :key="z" :value="z">{{ z }}</option>
            </select>
            <p class="text-[13px] text-ink-subtle">Schedule times are read in this zone.</p>
          </div>
        </div>

        <!-- Nothing above has touched the device yet. This is the one moment it does, and
             the loading/checkmark pair is what tells the user that a dropdown they just
             changed really did reach a physical screen. -->
        <div class="mt-5 flex items-center gap-3">
          <AppButton :disabled="!isDirty" :loading="isSaving" @click="onSave">
            Save changes
          </AppButton>
          <span v-if="isDirty && !isSaving" class="text-[13px] text-ink-subtle">
            Not sent to the screen yet
          </span>
          <span
            v-else-if="saveSucceeded"
            class="inline-flex items-center gap-1.5 text-[13px] text-ink-muted"
          >
            <svg viewBox="0 0 16 16" class="size-4 shrink-0" fill="none" aria-hidden="true">
              <circle cx="8" cy="8" r="7" class="stroke-current" stroke-width="1.5" />
              <path
                d="M5 8.2l2 2 4-4.4" class="stroke-current" stroke-width="1.5"
                stroke-linecap="round" stroke-linejoin="round"
              />
            </svg>
            Saved to the screen
          </span>
        </div>

        <!-- Single-device updates are owner-only, same as the rest of player build management —
             see backend/app/api/routes/devices.py's set_device_update. A web screen has no APK
             to install: it reloads onto the newest web player deploy by itself. -->
        <div v-if="isOwner && device.platform !== 'web'" class="mt-2 border-t border-line pt-6">
          <DeviceUpdateContainer
            :device="device"
            :is-saving="isSaving"
            :set-update="setForcedUpdate"
            :cancel-update="cancelForcedUpdate"
          />
        </div>

        <div class="mt-2 border-t border-line pt-6">
          <DeviceNowPlayingContainer :device-id="device.id" />
        </div>
      </template>

      <template v-else-if="tab === 'settings'">
        <DeviceSettingsContainer
          :device-id="device.id"
          :orientation="device.orientation"
          :platform="device.platform"
          :save-device="save"
        />
      </template>

      <template v-else>
        <DeviceActivityContainer :device-id="device.id" />
      </template>
    </template>

    <AppModal
      v-if="confirmingDisconnect"
      title="Disconnect this screen?"
      @close="disconnectState === 'disconnecting' ? undefined : (confirmingDisconnect = false)"
    >
      <p v-if="!handshake" class="text-sm text-ink-muted">
        {{ device?.name }} will be removed from your account. The screen is told straight away:
        it forgets this account's content and settings, wakes up if it was asleep, and shows a
        new pairing code — read that off the screen to add it back.
      </p>

      <div v-if="handshake" class="flex flex-col items-center gap-1 rounded-lg bg-surface px-3 py-3">
        <ConnectAnimation :state="handshake" />
        <p v-if="handshake === 'disconnecting'" class="text-[13px] text-ink-muted">
          Telling {{ device?.name }} to reset…
        </p>
        <p v-else-if="disconnectState === 'disconnected'" class="text-[13px] text-ink">
          {{ device?.name }} disconnected — it's showing a pairing code now
        </p>
        <p v-else-if="disconnectState === 'removed'" class="text-[13px] text-ink-muted">
          {{ device?.name }} didn't answer — it's offline. It's been removed anyway, and will
          start pairing by itself the next time it connects.
        </p>
      </div>

      <AppAlert v-if="disconnectState === 'failed' && saveError" tone="danger">{{ saveError }}</AppAlert>

      <ModalActions v-if="disconnectState === 'idle' || disconnectState === 'failed'">
        <AppButton variant="secondary" size="sm" @click="confirmingDisconnect = false">Cancel</AppButton>
        <AppButton variant="danger" size="sm" @click="onDisconnect">
          {{ disconnectState === 'failed' ? 'Try again' : 'Disconnect' }}
        </AppButton>
      </ModalActions>
    </AppModal>

  </div>
</template>
