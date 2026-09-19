<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import IconDoNotTouch from '~icons/material-symbols/do-not-touch'
import IconPause from '~icons/material-symbols/pause'
import IconPowerSettingsNew from '~icons/material-symbols/power-settings-new'
import IconSchedule from '~icons/material-symbols/schedule'
import IconTouchApp from '~icons/material-symbols/touch-app'

import { useDevicePower } from '@/hooks/useDevicePower'
import { useDeviceSettings } from '@/hooks/useDeviceSettings'
import { useFormat } from '@/hooks/useFormat'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import AppSwitch from '@/reusables/AppSwitch.vue'
import { ALL_DAYS, DAY_BITS, WEEKDAYS, WEEKENDS } from '@/types/api'
import type { DeviceOrientation, DevicePlatform, DeviceUpdateBody } from '@/types/api'
import { ORIENTATIONS } from '@/utils/orientation'

const props = defineProps<{
  deviceId: string
  /** Rotation is a field on the device row, not one of its remote settings. It belongs in this
   *  tab because this is where someone setting a screen up looks for it — mounting a panel
   *  sideways is configuration, not an edit to the device's name — but it saves through the
   *  device endpoint, which is why the parent hands its save down rather than this owning one. */
  orientation: DeviceOrientation
  /** A web screen has no app to exit, so the exit PIN is not offered for it. */
  platform: DevicePlatform
  saveDevice: (body: DeviceUpdateBody) => Promise<boolean>
}>()

/** The one spec whose value does not live in the settings store — see the prop above. */
const ORIENTATION_KEY = 'orientation'

const { isLoading, isSaving, error, value, reportedValue, setMany } = useDeviceSettings(props.deviceId)
const { status: power, isActing: powerActing, error: powerError, refresh: refreshPower, override, resume } =
  useDevicePower(props.deviceId)
const { relativeTime } = useFormat()

interface PowerScheduleValue {
  enabled: boolean
  days_of_week: number
  power_on: string
  power_off: string
}

/**
 * Every remotely-configurable setting this app knows how to show, in one place. Adding a new
 * one is a new entry here — plus, only if its shape is genuinely new, one more `kind` branch
 * in the template below. The hook, the API call, the draft row, and the backend route are
 * already generic over the key; nothing else about this file changes.
 */
type SettingSpec =
  | { key: string; label: string; description: string; kind: 'slider'; min: number; max: number; unit?: string }
  | { key: string; label: string; description: string; kind: 'toggle'; onLabel?: string; offLabel?: string }
  | { key: string; label: string; description: string; kind: 'text'; mask?: boolean; maxLength?: number }
  | { key: string; label: string; description: string; kind: 'select'; options: { value: string; label: string }[] }
  | { key: string; label: string; description: string; kind: 'power_schedule' }

const SETTINGS: SettingSpec[] = [
  {
    key: ORIENTATION_KEY, label: 'Rotation', kind: 'select',
    options: ORIENTATIONS.map((o) => ({ value: o.value, label: `${o.label} · ${o.hint}` })),
    description: 'How the panel is mounted, as the turn applied to what it shows. The screen turns as soon as it picks this up.',
  },
  {
    key: 'volume', label: 'Volume', kind: 'slider', min: 0, max: 100, unit: '%',
    description: 'Remote speaker volume.',
  },
  // Brightness is out for now — it silently does nothing on Device Owner hardware today
  // (writing Settings.System.SCREEN_BRIGHTNESS needs the WRITE_SETTINGS app-op, which Device
  // Owner status does not auto-grant the way it does for DevicePolicyManager-mediated calls
  // like lockNow()). Re-add once that's actually fixed on the player side.
  {
    key: 'touchscreen_disabled', label: 'Touchscreen', kind: 'toggle',
    description: "Disable touch input so the screen can't be interacted with directly.",
  },
  {
    key: 'app_password', label: 'App lock PIN', kind: 'text', mask: true, maxLength: 20,
    description: 'Required on the screen to exit the player app.',
  },
  {
    key: 'power_schedule', label: 'Power schedule', kind: 'power_schedule',
    description: 'Turn the screen on and off automatically, on its own days and times.',
  },
]

// The schedule renders inside the Power card (see the template) rather than through the
// generic per-spec loop — it and the on/off actions are one feature to whoever is configuring
// it, not two unrelated settings that happen to both be about power.
const listedSettings = computed(() =>
  SETTINGS.filter((s) => s.key !== 'power_schedule' && !(props.platform === 'web' && s.key === 'app_password')),
)
const powerScheduleSpec = SETTINGS.find((s) => s.key === 'power_schedule')!

function defaultFor(spec: SettingSpec): unknown {
  switch (spec.kind) {
    case 'slider': return spec.min
    case 'toggle': return false
    case 'text': return ''
    case 'select': return spec.options[0].value
    case 'power_schedule':
      return { enabled: false, days_of_week: ALL_DAYS, power_on: '08:00', power_off: '22:00' } satisfies PowerScheduleValue
  }
}

// Staged the same way every other device-affecting control in this app is: nothing reaches
// the screen until "Save changes" is clicked, keyed by setting so rows don't interfere with
// each other. The power on/off actions are the exception — see useDevicePower.
const drafts = reactive<Record<string, unknown>>({})
const justSaved = ref(false)

/** What a control should show before anyone touches it: the CMS's own stored value if one has
 *  ever been set, else whatever the device itself last reported for this key — so opening
 *  Settings on a screen nobody has configured yet shows its actual current volume, not a
 *  misleading 0%. Only falls back to a hardcoded default when neither exists at all. */
function currentValue(spec: SettingSpec): unknown {
  // Rotation's confirmed value is the device's own field, not anything in the settings store.
  if (spec.key === ORIENTATION_KEY) return props.orientation
  const stored = value(spec.key)
  if (stored !== undefined && stored !== null) return stored
  const reported = reportedValue(spec.key)
  if (reported !== undefined && reported !== null) return reported
  return defaultFor(spec)
}

function draftValue(spec: SettingSpec): unknown {
  return spec.key in drafts ? drafts[spec.key] : currentValue(spec)
}

/** Only the power-schedule kind needs its typed shape back out — everywhere else works with
 *  the primitive `unknown` directly. */
function powerDraft(spec: SettingSpec): PowerScheduleValue {
  return draftValue(spec) as PowerScheduleValue
}

function isDirty(spec: SettingSpec): boolean {
  if (!(spec.key in drafts)) return false
  // JSON comparison, not `!==`: power_schedule's draft is an object, and this has to work for
  // every kind without a per-kind branch.
  return JSON.stringify(drafts[spec.key]) !== JSON.stringify(currentValue(spec))
}

const dirtySpecs = computed(() => SETTINGS.filter(isDirty))
const anyDirty = computed(() => dirtySpecs.value.length > 0 || powerAction.value !== null)

function setDraft(spec: SettingSpec, next: unknown) {
  drafts[spec.key] = next
  justSaved.value = false
}

function onSlider(spec: SettingSpec, e: Event) {
  setDraft(spec, Number((e.target as HTMLInputElement).value))
}
function onText(spec: SettingSpec, e: Event) {
  setDraft(spec, (e.target as HTMLInputElement).value)
}
function onSelect(spec: SettingSpec, e: Event) {
  setDraft(spec, (e.target as HTMLSelectElement).value)
}
function onPowerScheduleField(spec: SettingSpec, patch: Partial<PowerScheduleValue>) {
  setDraft(spec, { ...powerDraft(spec), ...patch })
}
function togglePowerDay(spec: SettingSpec, bit: number) {
  onPowerScheduleField(spec, { days_of_week: powerDraft(spec).days_of_week ^ bit })
}

/** Only sliders (volume/brightness) have a device-reported value today — see
 *  `DeviceSettingsApplier.currentSettings` on the player side. Everything else is either
 *  read-only from the CMS's perspective or has no genuinely observable system state. */
function reportedCaption(spec: SettingSpec): string | undefined {
  if (spec.kind !== 'slider') return undefined
  const reported = reportedValue(spec.key)
  if (typeof reported !== 'number') return undefined
  return `Currently ${reported}${spec.unit ?? ''}`
}

async function onSaveAll() {
  const dirty = dirtySpecs.value
  let ok = true
  const settingsDirty = dirty.filter((spec) => spec.key !== ORIENTATION_KEY)
  if (settingsDirty.length) {
    const failedKeys = await setMany(settingsDirty.map((spec) => ({ key: spec.key, value: drafts[spec.key] })))
    for (const spec of settingsDirty) {
      if (!failedKeys.includes(spec.key)) delete drafts[spec.key]
    }
    ok = failedKeys.length === 0
  }
  // Same click and same staging as every row above, but a different request: rotation is a
  // device field, so it goes through the device endpoint the parent owns.
  if (dirty.some((spec) => spec.key === ORIENTATION_KEY)) {
    const done = await props.saveDevice({ orientation: drafts[ORIENTATION_KEY] as DeviceOrientation })
    if (done) delete drafts[ORIENTATION_KEY]
    ok = ok && done
  }
  // After the schedule, never before: an override made with a schedule on ends at that
  // schedule's next change, so it has to be worked out against the one just saved.
  const action = powerAction.value
  if (action) {
    const done = action === 'resume' ? await resume() : await override(action)
    if (done) powerAction.value = null
    ok = ok && done
  } else if (dirty.some((s) => s.key === 'power_schedule')) {
    // A schedule change can change what power should be right now.
    await refreshPower()
  }
  justSaved.value = ok
  if (ok) setTimeout(() => { justSaved.value = false }, 2500)
}

// --- Power -------------------------------------------------------------------------------

/** Staged like every other row: nothing reaches the screen until "Save changes". */
type PowerAction = 'on' | 'off' | 'resume'
const powerAction = ref<PowerAction | null>(null)

/** What "Turn … now" switches to — the opposite of what the screen should be doing. */
const nowTarget = computed<'on' | 'off'>(() => (power.value?.state === 'on' ? 'off' : 'on'))

const switchOn = computed(() =>
  powerAction.value === 'on' || powerAction.value === 'off'
    ? powerAction.value === 'on'
    : power.value?.state === 'on',
)

function stagePower(action: PowerAction) {
  // Pressing a staged action again takes it back.
  powerAction.value = powerAction.value === action ? null : action
  justSaved.value = false
}

function onPowerSwitch(on: boolean) {
  const target = on ? 'on' : 'off'
  // Flipping back to what the screen already is leaves nothing to send.
  powerAction.value = target === power.value?.state ? null : target
  justSaved.value = false
}

const stagedPowerLine = computed(() => {
  if (powerAction.value === 'resume') return 'Schedule resumes on save'
  if (powerAction.value) return `Turns ${powerAction.value} on save`
  return ''
})

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

/** "22:00", "tomorrow 08:00" or "Mon 08:00" — read straight off the device-local ISO strings
 *  the API returns, so it's the screen's wall clock, never the browser's. */
function whenLabel(iso: string): string {
  if (!power.value) return iso
  const time = iso.slice(11, 16)
  const day = iso.slice(0, 10)
  const today = power.value.device_local_time.slice(0, 10)
  if (day === today) return time
  const [y, m, d] = day.split('-').map(Number)
  const [ty, tm, td] = today.split('-').map(Number)
  const diff = Math.round((Date.UTC(y, m - 1, d) - Date.UTC(ty, tm - 1, td)) / 86_400_000)
  if (diff === 1) return `tomorrow ${time}`
  const weekday = new Date(Date.UTC(y, m - 1, d)).toLocaleDateString(undefined, { weekday: 'short', timeZone: 'UTC' })
  return `${weekday} ${time}`
}

const powerLine = computed(() => {
  const p = power.value
  if (!p) return ''
  const state = cap(p.state)
  if (p.source === 'schedule') {
    return p.until ? `${state} · by schedule · ${p.state === 'on' ? 'off' : 'on'} at ${whenLabel(p.until)}` : `${state} · by schedule`
  }
  if (p.source === 'override' && p.schedule_enabled) return `${state} · turned ${p.state} manually`
  return state
})

/** True while a manual change is holding the schedule back — the one state that needs to be
 *  loud, because it's the one where the screen isn't doing what its schedule says. */
const schedulePaused = computed(() => power.value?.source === 'override' && power.value.schedule_enabled)

/** Only worth showing when the screen disagrees with what it should be — agreement is the
 *  normal case and needs no words. */
const reportedMismatch = computed(() => {
  const p = power.value
  return !!p?.reported_state && p.reported_state !== p.state
})
</script>

<template>
  <div class="flex flex-col gap-4">
    <h2 class="text-lg">Settings</h2>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>

    <ul v-else class="flex flex-col gap-2">
      <li v-for="spec in listedSettings" :key="spec.key">
        <AppCard>
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="min-w-0">
              <p class="text-sm text-ink">{{ spec.label }}</p>
              <p class="mt-0.5 text-[13px] text-ink-muted">{{ spec.description }}</p>
              <p v-if="reportedCaption(spec)" class="mt-0.5 text-[13px] text-ink-subtle">
                {{ reportedCaption(spec) }}
              </p>
            </div>

            <div class="flex shrink-0 items-center gap-3">
              <template v-if="spec.kind === 'slider'">
                <input
                  type="range" :min="spec.min" :max="spec.max"
                  :value="draftValue(spec)"
                  class="h-1.5 w-36 cursor-pointer accent-ink"
                  @input="onSlider(spec, $event)"
                />
                <span class="w-10 shrink-0 text-right text-[13px] text-ink-muted">
                  {{ draftValue(spec) }}{{ spec.unit }}
                </span>
              </template>

              <template v-else-if="spec.kind === 'toggle'">
                <component
                  v-if="spec.key === 'touchscreen_disabled'"
                  :is="draftValue(spec) ? IconDoNotTouch : IconTouchApp"
                  class="size-4 shrink-0 text-ink-muted"
                />
                <span class="text-[13px] text-ink-muted">
                  {{ draftValue(spec) ? (spec.onLabel ?? 'Disabled') : (spec.offLabel ?? 'Enabled') }}
                </span>
                <AppSwitch
                  :model-value="!(draftValue(spec) as boolean)"
                  @update:model-value="setDraft(spec, !$event)"
                />
              </template>

              <input
                v-else-if="spec.kind === 'text'"
                :type="spec.mask ? 'password' : 'text'"
                :maxlength="spec.maxLength"
                :value="draftValue(spec) as string"
                class="w-36 rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px]
                       text-ink focus:border-ink focus:outline-none"
                @input="onText(spec, $event)"
              />

              <select
                v-else-if="spec.kind === 'select'"
                class="rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px]
                       text-ink focus:border-ink focus:outline-none"
                :value="draftValue(spec) as string"
                @change="onSelect(spec, $event)"
              >
                <option v-for="opt in spec.options" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>

              <!-- A genuinely new control shape (not slider/toggle/text/select) gets one more
                   branch here — everything else on this row is already generic. -->
            </div>
          </div>
        </AppCard>
      </li>

      <!-- Power: what the screen is doing and why, the one action that changes it now, and the
           schedule that normally runs it — one card. With a schedule, the on/off switch
           becomes a "turn off/on now" action that ends by itself at the next scheduled change,
           so the two can never silently disagree. -->
      <li>
        <AppCard>
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="min-w-0">
              <p class="flex items-center gap-1.5 text-sm text-ink">
                <IconPowerSettingsNew class="size-4 shrink-0 text-ink-muted" />
                Power
              </p>
              <p v-if="power" class="mt-0.5 text-[13px] text-ink-muted">{{ powerLine }}</p>
              <p v-if="stagedPowerLine" class="mt-0.5 text-[13px] text-ink-subtle">{{ stagedPowerLine }}</p>
              <p v-if="power && reportedMismatch" class="mt-0.5 text-[13px] text-danger">
                Screen reports {{ power.reported_state }} · {{ relativeTime(power.reported_at) }}
              </p>
              <p v-if="power" class="mt-1 text-[12px] text-ink-subtle">
                Off shows a black screen with nothing playing and lets the panel sleep.
                <template v-if="platform !== 'web'">A screen set up as Device Owner switches its display off as well.</template>
              </p>
            </div>

            <!-- Follows the schedule as drafted, so the control matches what Save will send. -->
            <template v-if="power">
              <AppButton
                v-if="powerDraft(powerScheduleSpec).enabled"
                :variant="powerAction === nowTarget ? 'primary' : 'secondary'" size="sm"
                :disabled="powerActing"
                @click="stagePower(nowTarget)"
              >
                Turn {{ nowTarget }} now
              </AppButton>
              <AppSwitch
                v-else
                :model-value="switchOn"
                :disabled="powerActing"
                @update:model-value="onPowerSwitch"
              />
            </template>
          </div>

          <div
            v-if="schedulePaused && power?.until"
            class="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg bg-raised px-3 py-2"
          >
            <span class="flex items-center gap-1.5 text-[13px] text-ink-muted">
              <IconPause class="size-4 shrink-0" />
              Schedule paused until {{ whenLabel(power.until) }}
            </span>
            <AppButton
              :variant="powerAction === 'resume' ? 'primary' : 'secondary'" size="sm"
              :disabled="powerActing"
              @click="stagePower('resume')"
            >
              Resume schedule
            </AppButton>
          </div>

          <AppAlert v-if="powerError" tone="danger" class="mt-3">{{ powerError }}</AppAlert>

          <div class="mt-3 flex flex-col gap-3 border-t border-line pt-3">
            <div class="flex items-center justify-between gap-3">
              <p class="flex items-center gap-1.5 text-[13px] text-ink-muted">
                <IconSchedule class="size-4 shrink-0" />
                Schedule
              </p>
              <AppSwitch
                :model-value="powerDraft(powerScheduleSpec).enabled"
                @update:model-value="onPowerScheduleField(powerScheduleSpec, { enabled: $event })"
              />
            </div>

            <template v-if="powerDraft(powerScheduleSpec).enabled">
              <div class="flex flex-wrap gap-1">
                <button
                  v-for="d in DAY_BITS"
                  :key="d.bit"
                  type="button"
                  class="rounded-full border px-2.5 py-1 text-[13px] transition-colors duration-200"
                  :class="powerDraft(powerScheduleSpec).days_of_week & d.bit
                    ? 'border-ink bg-ink text-ink-inverse'
                    : 'border-line-strong text-ink-muted hover:bg-raised'"
                  @click="togglePowerDay(powerScheduleSpec, d.bit)"
                >
                  {{ d.short }}
                </button>
              </div>
              <div class="flex gap-2">
                <button type="button" class="text-[13px] text-ink underline underline-offset-2"
                        @click="onPowerScheduleField(powerScheduleSpec, { days_of_week: WEEKDAYS })">Weekdays</button>
                <button type="button" class="text-[13px] text-ink underline underline-offset-2"
                        @click="onPowerScheduleField(powerScheduleSpec, { days_of_week: WEEKENDS })">Weekends</button>
                <button type="button" class="text-[13px] text-ink underline underline-offset-2"
                        @click="onPowerScheduleField(powerScheduleSpec, { days_of_week: ALL_DAYS })">Every day</button>
              </div>

              <div class="grid max-w-xs grid-cols-2 gap-3">
                <div class="flex flex-col gap-1.5">
                  <label class="text-[13px] text-ink-muted">On</label>
                  <input
                    type="time" :value="powerDraft(powerScheduleSpec).power_on"
                    class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm
                           text-ink focus:border-ink focus:outline-none"
                    @input="onPowerScheduleField(powerScheduleSpec, { power_on: ($event.target as HTMLInputElement).value })"
                  />
                </div>
                <div class="flex flex-col gap-1.5">
                  <label class="text-[13px] text-ink-muted">Off</label>
                  <input
                    type="time" :value="powerDraft(powerScheduleSpec).power_off"
                    class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm
                           text-ink focus:border-ink focus:outline-none"
                    @input="onPowerScheduleField(powerScheduleSpec, { power_off: ($event.target as HTMLInputElement).value })"
                  />
                </div>
              </div>
            </template>
          </div>
        </AppCard>
      </li>
    </ul>

    <!-- One save for every setting, staged above: matches DeviceDetailContainer's own
         "Manage" tab rather than a per-row send. -->
    <div v-if="!isLoading" class="flex items-center gap-3">
      <AppButton :disabled="!anyDirty" :loading="isSaving || powerActing" @click="onSaveAll">
        Save changes
      </AppButton>
      <span v-if="anyDirty && !isSaving && !powerActing" class="text-[13px] text-ink-subtle">
        Not sent to the screen yet
      </span>
      <span
        v-else-if="justSaved"
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
  </div>
</template>
