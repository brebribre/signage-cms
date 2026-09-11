<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import { useDeviceSettings } from '@/hooks/useDeviceSettings'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import { ALL_DAYS, DAY_BITS, WEEKDAYS, WEEKENDS } from '@/types/api'

const props = defineProps<{ deviceId: string }>()

const { isLoading, isSaving, error, value, reportedValue, setMany } = useDeviceSettings(props.deviceId)

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
  | { key: string; label: string; description: string; kind: 'power_schedule' }

const SETTINGS: SettingSpec[] = [
  {
    key: 'volume', label: 'Volume', kind: 'slider', min: 0, max: 100, unit: '%',
    description: 'Remote speaker volume.',
  },
  {
    key: 'brightness', label: 'Brightness', kind: 'slider', min: 0, max: 100, unit: '%',
    description: 'Screen backlight level.',
  },
  {
    key: 'touchscreen_disabled', label: 'Touchscreen', kind: 'toggle',
    description: "Disable touch input so the screen can't be interacted with directly.",
  },
  {
    key: 'app_password', label: 'App lock PIN', kind: 'text', mask: true, maxLength: 20,
    description: 'Required on the device to exit the player app.',
  },
  {
    key: 'power_schedule', label: 'Power on/off', kind: 'power_schedule',
    description: 'Turn the screen hardware on and off automatically, on its own days and times.',
  },
  {
    key: 'power_on', label: 'Power (manual)', kind: 'toggle', onLabel: 'On', offLabel: 'Off',
    description: 'Direct override, ignoring the schedule above — for testing power control itself.',
  },
]

function defaultFor(spec: SettingSpec): unknown {
  switch (spec.kind) {
    case 'slider': return spec.min
    case 'toggle': return false
    case 'text': return ''
    case 'power_schedule':
      return { enabled: false, days_of_week: ALL_DAYS, power_on: '08:00', power_off: '22:00' } satisfies PowerScheduleValue
  }
}

// Staged the same way every other device-affecting control in this app is: nothing reaches
// the screen until "Save changes" is clicked, keyed by setting so rows don't interfere with
// each other.
const drafts = reactive<Record<string, unknown>>({})
const justSaved = ref(false)

function currentValue(spec: SettingSpec): unknown {
  const stored = value(spec.key)
  return stored === undefined ? defaultFor(spec) : stored
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
const anyDirty = computed(() => dirtySpecs.value.length > 0)

function setDraft(spec: SettingSpec, next: unknown) {
  drafts[spec.key] = next
  justSaved.value = false
}

function onSlider(spec: SettingSpec, e: Event) {
  setDraft(spec, Number((e.target as HTMLInputElement).value))
}
function onToggle(spec: SettingSpec, e: Event) {
  setDraft(spec, (e.target as HTMLInputElement).checked)
}
function onText(spec: SettingSpec, e: Event) {
  setDraft(spec, (e.target as HTMLInputElement).value)
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
  const failedKeys = await setMany(dirty.map((spec) => ({ key: spec.key, value: drafts[spec.key] })))
  for (const spec of dirty) {
    if (!failedKeys.includes(spec.key)) delete drafts[spec.key]
  }
  justSaved.value = failedKeys.length === 0
  if (justSaved.value) setTimeout(() => { justSaved.value = false }, 2500)
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <h2 class="text-lg">Settings</h2>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>

    <ul v-else class="flex flex-col gap-2">
      <li v-for="spec in SETTINGS" :key="spec.key">
        <AppCard>
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="min-w-0">
              <p class="text-sm text-ink">{{ spec.label }}</p>
              <p class="mt-0.5 text-[13px] text-ink-muted">{{ spec.description }}</p>
              <p v-if="reportedCaption(spec)" class="mt-0.5 text-[13px] text-ink-subtle">
                {{ reportedCaption(spec) }}
              </p>
            </div>

            <div v-if="spec.kind !== 'power_schedule'" class="flex shrink-0 items-center gap-3">
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

              <label v-else-if="spec.kind === 'toggle'" class="flex cursor-pointer items-center gap-2">
                <input
                  type="checkbox" class="size-4 accent-ink"
                  :checked="draftValue(spec) as boolean"
                  @change="onToggle(spec, $event)"
                />
                <span class="text-[13px] text-ink-muted">
                  {{ draftValue(spec) ? (spec.onLabel ?? 'Disabled') : (spec.offLabel ?? 'Enabled') }}
                </span>
              </label>

              <input
                v-else-if="spec.kind === 'text'"
                :type="spec.mask ? 'password' : 'text'"
                :maxlength="spec.maxLength"
                :value="draftValue(spec) as string"
                class="w-36 rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px]
                       text-ink focus:border-ink focus:outline-none"
                @input="onText(spec, $event)"
              />

              <!-- A genuinely new control shape (not slider/toggle/text) gets one more
                   branch here — everything else on this row is already generic. -->
            </div>
          </div>

          <!-- power_schedule needs more room than a row can give it (days + two times), so
               it gets a panel below the label instead of the inline control other kinds
               use. -->
          <div v-if="spec.kind === 'power_schedule'" class="mt-3 flex flex-col gap-3 border-t border-line pt-3">
            <label class="flex w-fit cursor-pointer items-center gap-2">
              <input
                type="checkbox" class="size-4 accent-ink"
                :checked="powerDraft(spec).enabled"
                @change="onPowerScheduleField(spec, { enabled: ($event.target as HTMLInputElement).checked })"
              />
              <span class="text-[13px] text-ink-muted">Enabled</span>
            </label>

            <div class="flex flex-wrap gap-1">
              <button
                v-for="d in DAY_BITS"
                :key="d.bit"
                type="button"
                class="rounded-full border-2 px-2.5 py-1 text-[13px] transition-colors duration-200"
                :class="powerDraft(spec).days_of_week & d.bit
                  ? 'border-ink bg-ink text-ink-inverse'
                  : 'border-line-strong text-ink-muted hover:bg-raised'"
                @click="togglePowerDay(spec, d.bit)"
              >
                {{ d.short }}
              </button>
            </div>
            <div class="flex gap-2">
              <button type="button" class="text-[13px] text-ink underline underline-offset-2"
                      @click="onPowerScheduleField(spec, { days_of_week: WEEKDAYS })">Weekdays</button>
              <button type="button" class="text-[13px] text-ink underline underline-offset-2"
                      @click="onPowerScheduleField(spec, { days_of_week: WEEKENDS })">Weekends</button>
              <button type="button" class="text-[13px] text-ink underline underline-offset-2"
                      @click="onPowerScheduleField(spec, { days_of_week: ALL_DAYS })">Every day</button>
            </div>

            <div class="grid max-w-xs grid-cols-2 gap-3">
              <div class="flex flex-col gap-1.5">
                <label class="text-[13px] text-ink-muted">Power on</label>
                <input
                  type="time" :value="powerDraft(spec).power_on"
                  class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm
                         text-ink focus:border-ink focus:outline-none"
                  @input="onPowerScheduleField(spec, { power_on: ($event.target as HTMLInputElement).value })"
                />
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="text-[13px] text-ink-muted">Power off</label>
                <input
                  type="time" :value="powerDraft(spec).power_off"
                  class="rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm
                         text-ink focus:border-ink focus:outline-none"
                  @input="onPowerScheduleField(spec, { power_off: ($event.target as HTMLInputElement).value })"
                />
              </div>
            </div>
          </div>
        </AppCard>
      </li>
    </ul>

    <!-- One save for every setting, staged above: matches DeviceDetailContainer's own
         "Manage" tab rather than a per-row send. -->
    <div v-if="!isLoading" class="flex items-center gap-3">
      <AppButton :disabled="!anyDirty" :loading="isSaving" @click="onSaveAll">
        Save changes
      </AppButton>
      <span v-if="anyDirty && !isSaving" class="text-[13px] text-ink-subtle">
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
