<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import DeviceActivityContainer from '@/containers/DeviceActivityContainer.vue'
import DeviceScheduleContainer from '@/containers/DeviceScheduleContainer.vue'
import { useDeviceDetail } from '@/hooks/useDeviceDetail'
import { useFormat } from '@/hooks/useFormat'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import AppInput from '@/reusables/AppInput.vue'
import AppModal from '@/reusables/AppModal.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import StatusDot from '@/reusables/StatusDot.vue'
import type { DeviceOrientation } from '@/types/api'

const route = useRoute()
const router = useRouter()
const id = String(route.params.id)

const {
  device, isLoading, isSaving, error, saveError, saveSucceeded, freshPairing,
  save, unpair, remove,
} = useDeviceDetail(id)
const { dimensions, relativeTime, date } = useFormat()

const confirmingUnpair = ref(false)
const confirmingDelete = ref(false)

const TABS = ['manage', 'activity'] as const
const tab = ref<(typeof TABS)[number]>('manage')

// Everything below is a draft the user is composing — nothing here reaches the device until
// "Save changes" is clicked. Re-seeded whenever the confirmed device state changes, so a
// background refresh (or a save just landing) doesn't leave the form disagreeing with what
// the device actually has.
const form = reactive({
  name: '',
  location: '',
  orientation: 'landscape' as DeviceOrientation,
  timezone: 'UTC',
})

watch(device, (d) => {
  if (!d) return
  form.name = d.name
  form.location = d.location
  form.orientation = d.orientation
  form.timezone = d.timezone
}, { immediate: true })

const isDirty = computed(() => {
  const d = device.value
  if (!d) return false
  return form.name !== d.name
    || form.location !== d.location
    || form.orientation !== d.orientation
    || form.timezone !== d.timezone
})

const COMMON_ZONES = [
  'UTC',
  'Asia/Jakarta',
  'Asia/Singapore',
  'Asia/Kuala_Lumpur',
  'Asia/Bangkok',
  'Asia/Tokyo',
  'Australia/Sydney',
  'Europe/London',
  'Europe/Amsterdam',
  'America/New_York',
  'America/Los_Angeles',
]

/** The device's own zone always appears, even if it isn't in the short list above. */
const zoneOptions = computed(() => {
  const current = device.value?.timezone
  return current && !COMMON_ZONES.includes(current) ? [current, ...COMMON_ZONES] : COMMON_ZONES
})

function onOrientation(e: Event) {
  form.orientation = (e.target as HTMLSelectElement).value as DeviceOrientation
}

/**
 * One request carrying every field the user touched — a dropdown that looks as small as
 * "pick a playlist" is really "change what this screen shows in the next 30 seconds", and
 * it deserves the same explicit save and confirmation as everything else here rather than
 * firing the moment it's clicked.
 */
async function onSave() {
  const d = device.value
  if (!d) return
  await save({
    name: form.name,
    location: form.location,
    orientation: form.orientation,
    timezone: form.timezone,
  })
}

async function onUnpair() {
  await unpair()
  // Left open on purpose: freshPairing now holds the new code, and that is what the modal
  // shows next — closing here would throw away the one thing this action was for.
}

async function onDelete() {
  if (await remove()) router.push({ name: 'devices' })
  else confirmingDelete.value = false
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <AppButton variant="ghost" size="sm" class="self-start" @click="router.push({ name: 'devices' })">
      ← Devices
    </AppButton>

    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>
    <AppAlert v-else-if="error" tone="danger">{{ error }}</AppAlert>

    <template v-else-if="device">
      <PageTitle :title="device.name || 'Unnamed screen'">
        <template #actions>
          <div class="flex items-center gap-2">
            <AppButton variant="secondary" size="sm" @click="confirmingUnpair = true">
              Unpair
            </AppButton>
            <AppButton variant="danger" size="sm" @click="confirmingDelete = true">Delete</AppButton>
          </div>
        </template>
      </PageTitle>

      <AppAlert v-if="saveError" tone="danger">{{ saveError }}</AppAlert>

      <AppCard>
        <dl class="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
          <div>
            <dt class="text-[13px] text-ink-muted">Status</dt>
            <dd class="mt-0.5"><StatusDot :last-seen-at="device.last_seen_at" /></dd>
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
            <dt class="text-[13px] text-ink-muted">App version</dt>
            <dd class="text-sm text-ink">{{ device.app_version ?? '—' }}</dd>
          </div>
        </dl>
      </AppCard>

      <!-- Same pill style as the Activity sub-tabs below, so the two tab rows in this page
           read as one pattern rather than two different widgets. -->
      <div class="flex items-center gap-2 border-b border-line pb-4">
        <button
          v-for="t in TABS"
          :key="t"
          type="button"
          class="rounded-full border-2 px-3 py-1 text-[13px] transition-colors duration-200"
          :class="tab === t
            ? 'border-ink bg-ink text-ink-inverse'
            : 'border-line-strong text-ink-muted hover:bg-raised'"
          @click="tab = t"
        >
          {{ t === 'manage' ? 'Manage' : 'Errors & logs' }}
        </button>
      </div>

      <template v-if="tab === 'manage'">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <AppInput id="dev-name" v-model="form.name" label="Name" />
          <AppInput id="dev-location" v-model="form.location" label="Location" />

          <div class="flex flex-col gap-1.5">
            <label class="text-[13px] text-ink-muted">Orientation</label>
            <select
              class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm text-ink
                     focus:border-ink focus:outline-none"
              :value="form.orientation"
              @change="onOrientation"
            >
              <option value="landscape">Landscape</option>
              <option value="portrait">Portrait</option>
            </select>
          </div>

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

        <!-- Read-only: what this screen plays and when is decided in Campaigns, not here. -->
        <div class="mt-2 border-t border-line pt-6">
          <DeviceScheduleContainer :device-id="device.id" :timezone="device.timezone" />
        </div>
      </template>

      <template v-else>
        <DeviceActivityContainer :device-id="device.id" />
      </template>
    </template>

    <AppModal v-if="confirmingUnpair" title="Unpair this screen?" @close="confirmingUnpair = false">
      <template v-if="!freshPairing">
        <p class="text-sm text-ink-muted">
          The screen's current token stops working immediately and it falls back to showing a
          pairing code. Its name, location and playlist are kept — re-pairing does not mean
          setting it up again.
        </p>
        <div class="mt-4 flex justify-end gap-2">
          <AppButton variant="secondary" size="sm" @click="confirmingUnpair = false">Cancel</AppButton>
          <AppButton variant="danger" size="sm" :loading="isSaving" @click="onUnpair">Unpair</AppButton>
        </div>
      </template>
      <template v-else>
        <p class="text-sm text-ink-muted">
          Unpaired. The screen will show this same code once it notices — claim it again with:
        </p>
        <p class="mt-2 text-center text-2xl tracking-widest text-ink">{{ freshPairing.pairing_code }}</p>
        <div class="mt-4 flex justify-end">
          <AppButton size="sm" @click="confirmingUnpair = false">Done</AppButton>
        </div>
      </template>
    </AppModal>

    <AppModal v-if="confirmingDelete" title="Delete this screen?" @close="confirmingDelete = false">
      <p class="text-sm text-ink-muted">
        {{ device?.name }} will be removed from your account. If the hardware is still running,
        its token stops working and it starts pairing again on its own — read the new code off
        the screen to add it back.
      </p>
      <div class="mt-4 flex justify-end gap-2">
        <AppButton variant="secondary" size="sm" @click="confirmingDelete = false">Cancel</AppButton>
        <AppButton variant="danger" size="sm" @click="onDelete">Delete</AppButton>
      </div>
    </AppModal>
  </div>
</template>
