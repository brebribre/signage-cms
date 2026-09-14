<script setup lang="ts">
/**
 * End-to-end deployment: screens → schedule → review, saved as one campaign. The same
 * `CampaignWrite` the campaign editor produces, reached as a guided flow instead of a form —
 * every rule shares one date range, and rules on this campaign may not overlap, so what the
 * timeline shows is exactly what plays: each window its playlist, everything else asleep.
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import IconAdd from '~icons/material-symbols/add'
import IconAddPhoto from '~icons/material-symbols/add-photo-alternate-outline'
import IconArrowBack from '~icons/material-symbols/arrow-back'
import IconArrowForward from '~icons/material-symbols/arrow-forward'
import IconCheck from '~icons/material-symbols/check'
import IconClose from '~icons/material-symbols/close'
import IconRocket from '~icons/material-symbols/rocket-launch-outline'

import PlaylistComposeContainer from '@/containers/PlaylistComposeContainer.vue'
import { useCampaignDetail } from '@/hooks/useCampaignDetail'
import { useCampaigns } from '@/hooks/useCampaigns'
import { useDevices } from '@/hooks/useDevices'
import { usePlaylists } from '@/hooks/usePlaylists'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import AppInput from '@/reusables/AppInput.vue'
import AppModal from '@/reusables/AppModal.vue'
import AppSwitch from '@/reusables/AppSwitch.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import PairScreenForm from '@/reusables/PairScreenForm.vue'
import PlaylistPicker from '@/reusables/PlaylistPicker.vue'
import StatusDot from '@/reusables/StatusDot.vue'
import StepIndicator from '@/reusables/StepIndicator.vue'
import WeekTimeline from '@/reusables/WeekTimeline.vue'
import { ALL_DAYS, DAY_BITS, WEEKDAYS, WEEKENDS } from '@/types/api'
import type { ClaimBody, PlaylistSummary } from '@/types/api'
import { crossesMidnight, toMinutes, windowLength, windowsOverlap } from '@/utils/scheduleMath'
import type { TimelineSlot, TimeWindow } from '@/utils/scheduleMath'

const router = useRouter()

const STEPS = ['Screens', 'Schedule', 'Review']
const step = ref(0)

// --- 1. Screens ---

const {
  items: devices, isLoading: devicesLoading, error: devicesError,
  isSaving: claiming, claimError, connecting, claim,
} = useDevices()

const { items: campaigns } = useCampaigns()
/** Screens already in a campaign aren't offered: two campaigns on one screen resolve by
 *  priority, which this flow deliberately never asks about. Keyed to the campaign's name so
 *  the card can say where the screen is used. */
const campaignByDevice = computed(() => {
  const map = new Map<string, string>()
  for (const c of campaigns.value) {
    for (const id of c.device_ids) if (!map.has(id)) map.set(id, c.name)
  }
  return map
})
const availableDevices = computed(() => devices.value.filter((d) => !campaignByDevice.value.has(d.id)))
/** Pickable screens first, taken ones sunk to the bottom — each group keeps the list's order. */
const orderedDevices = computed(() => [
  ...availableDevices.value,
  ...devices.value.filter((d) => campaignByDevice.value.has(d.id)),
])

const selectedIds = ref<string[]>([])
const isSelected = (id: string) => selectedIds.value.includes(id)
const allSelected = computed(
  () => availableDevices.value.length > 0 && availableDevices.value.every((d) => isSelected(d.id)),
)
function toggleDevice(id: string) {
  if (campaignByDevice.value.has(id)) return
  const at = selectedIds.value.indexOf(id)
  at >= 0 ? selectedIds.value.splice(at, 1) : selectedIds.value.push(id)
}
function toggleAll() {
  selectedIds.value = allSelected.value ? [] : availableDevices.value.map((d) => d.id)
}
// Campaigns can land after a screen was already picked — drop anything that turns out taken.
watch(campaignByDevice, (taken) => {
  selectedIds.value = selectedIds.value.filter((id) => !taken.has(id))
})

const pairing = ref(false)
async function onClaim(body: ClaimBody) {
  if (!(await claim(body))) return
  // Pairing from here means "I want to deploy to this one" — select it rather than making
  // them find it in the list they just added it to.
  if (connecting.value && !isSelected(connecting.value.id)) selectedIds.value.push(connecting.value.id)
  if (!claimError.value) {
    await new Promise((r) => setTimeout(r, 900))
    pairing.value = false
  }
}

// --- 2. Schedule ---

const { items: playlists, refresh: refreshPlaylists } = usePlaylists()
const playlistById = computed(() => new Map(playlists.value.map((p) => [p.id, p])))

interface Slot extends TimeWindow {
  key: string
  playlist_id: string
  all_day: boolean
}

/** The backend has no 24:00 and rejects start == end, so a whole day is spelled the way the
 *  campaign editor already spells it. */
const ALL_DAY = { starts_at: '00:00', ends_at: '23:59' } as const

/** The window a slot actually covers. All day overrides the typed times without discarding
 *  them, so switching it back off restores whatever was there. */
function effective(s: Slot): TimeWindow {
  return s.all_day ? { ...ALL_DAY, days_of_week: s.days_of_week } : s
}

function pad(n: number) {
  return String(n).padStart(2, '0')
}
function fromMinutes(minutes: number): string {
  const m = ((minutes % 1440) + 1440) % 1440
  return `${pad(Math.floor(m / 60))}:${pad(m % 60)}`
}
function localIsoDate(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function newSlot(starts_at: string, ends_at: string): Slot {
  return { key: crypto.randomUUID(), playlist_id: '', starts_at, ends_at, days_of_week: ALL_DAYS, all_day: false }
}

const slots = ref<Slot[]>([newSlot('09:00', '17:00')])
const fromDate = ref('')
const untilDate = ref('')
/** Missing-playlist errors wait for a Next attempt — a fresh row isn't a mistake yet. Clashes
 *  and bad times show immediately, since those are something just typed. */
const attempted = ref(false)

function addSlot() {
  const last = slots.value[slots.value.length - 1]
  if (!last || last.all_day) {
    slots.value.push(newSlot('09:00', '17:00'))
    return
  }
  // Pick up where the previous one ends — the common case is back-to-back windows.
  const start = toMinutes(last.ends_at)
  slots.value.push(newSlot(fromMinutes(start), fromMinutes(start + 120)))
}

const slotErrors = computed(() =>
  slots.value.map((s, i) => {
    const w = effective(s)
    if (!w.starts_at || !w.ends_at) return 'Set a start and end time'
    if (w.starts_at === w.ends_at) return 'Start and end must differ'
    if (!w.days_of_week) return 'Pick at least one day'
    const clash = slots.value.findIndex((other, j) => j !== i && windowsOverlap(w, effective(other)))
    if (clash >= 0) return `Overlaps with #${clash + 1}`
    return null
  }),
)
const shownError = (i: number) =>
  slotErrors.value[i] ?? (attempted.value && !slots.value[i].playlist_id ? 'Pick a playlist' : null)

const today = localIsoDate(new Date())
const dateError = computed(() => {
  if (fromDate.value && untilDate.value && untilDate.value < fromDate.value) return "Can't end before it starts"
  if (untilDate.value && untilDate.value < today) return 'Already ended'
  return null
})

const scheduleValid = computed(
  () =>
    slots.value.length > 0 &&
    !dateError.value &&
    slots.value.every((s, i) => s.playlist_id && !slotErrors.value[i]),
)

/** Same playlist, same tone — wherever it appears on the timeline. */
const toneByPlaylist = computed(() => {
  const ids = [...new Set(slots.value.map((s) => s.playlist_id).filter(Boolean))]
  return new Map(ids.map((id, i) => [id, i]))
})

const timelineSlots = computed<TimelineSlot[]>(() =>
  slots.value.flatMap((s, i) => {
    const w = effective(s)
    return s.playlist_id && windowLength(w)
      ? [{
          key: s.key, starts_at: w.starts_at, ends_at: w.ends_at, days_of_week: w.days_of_week,
          label: playlistById.value.get(s.playlist_id)?.name ?? '—',
          tone: toneByPlaylist.value.get(s.playlist_id) ?? 0,
          invalid: !!slotErrors.value[i],
        }]
      : []
  }),
)

/** Which slot the compose modal is for, and — when adding media rather than creating — which
 *  playlist it's adding to. */
const composing = ref<{ slotKey: string; playlist: PlaylistSummary | null } | null>(null)
async function onComposed(id: string) {
  await refreshPlaylists()
  const slot = slots.value.find((s) => s.key === composing.value?.slotKey)
  if (slot) slot.playlist_id = id
  composing.value = null
}

// --- 3. Review ---

const { isSaving: deploying, saveError, skippedDeviceIds, save } = useCampaignDetail(null)
const campaignName = ref('')
const deployedId = ref<string | null>(null)

const selectedDevices = computed(() => devices.value.filter((d) => isSelected(d.id)))
/** A screen with its own default playlist falls back to that — not to asleep — wherever no
 *  rule covers. Worth saying, because the timeline can't show it. */
const devicesWithDefault = computed(() => selectedDevices.value.filter((d) => d.playlist_id))
const sortedSlots = computed(() =>
  [...slots.value].sort((a, b) => effective(a).starts_at.localeCompare(effective(b).starts_at)),
)

function formatDate(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}
const dateSummary = computed(() => {
  if (fromDate.value && untilDate.value) return `${formatDate(fromDate.value)} – ${formatDate(untilDate.value)}`
  if (fromDate.value) return `From ${formatDate(fromDate.value)}`
  if (untilDate.value) return `Until ${formatDate(untilDate.value)}`
  return 'Ongoing'
})
function dayLabel(mask: number): string {
  if (mask === ALL_DAYS) return 'Every day'
  if (mask === WEEKDAYS) return 'Weekdays'
  if (mask === WEEKENDS) return 'Weekends'
  return DAY_BITS.filter((d) => mask & d.bit).map((d) => d.short).join(', ')
}

async function onDeploy() {
  deployedId.value = await save({
    name: campaignName.value.trim(),
    device_ids: selectedIds.value,
    rules: slots.value.map((s) => {
      const w = effective(s)
      return {
        playlist_id: s.playlist_id,
        days_of_week: w.days_of_week,
        starts_at: `${w.starts_at}:00`,
        ends_at: `${w.ends_at}:00`,
        start_date: fromDate.value || null,
        end_date: untilDate.value || null,
      }
    }),
  })
}

// --- Navigation ---

function next() {
  if (step.value === 0 && !selectedIds.value.length) return
  if (step.value === 1) {
    attempted.value = true
    if (!scheduleValid.value) return
    if (!campaignName.value) {
      campaignName.value = `Deployment · ${new Date().toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}`
    }
  }
  step.value++
}

// `appearance-none` + `min-w-0`: iOS Safari gives native date/time inputs an intrinsic width
// that ignores `w-*` and won't shrink inside a grid or flex cell, so they overflow their
// column — and a date input with no value collapses its height, hence the fixed `h-*`.
const TIME_INPUT =
  'h-9 w-[5.75rem] min-w-0 appearance-none rounded-lg border bg-canvas px-2 text-center text-sm tabular-nums text-ink ' +
  'focus:border-ink focus:outline-none disabled:cursor-not-allowed'
const DATE_INPUT =
  'h-10 w-full min-w-0 appearance-none rounded-lg border bg-canvas px-3 text-sm text-ink ' +
  'focus:border-ink focus:outline-none [&::-webkit-date-and-time-value]:text-left'
</script>

<template>
  <div class="flex flex-col gap-8">
    <PageTitle title="Deploy" />

    <!-- Done -->
    <div v-if="deployedId" class="flex flex-col items-center gap-4 rounded-xl bg-surface px-6 py-16 text-center">
      <span class="flex size-14 items-center justify-center rounded-full bg-ink text-ink-inverse">
        <IconCheck class="size-7" />
      </span>
      <div>
        <h2 class="text-2xl">Deployed</h2>
        <p class="mt-1 text-sm text-ink-muted">
          {{ selectedIds.length - skippedDeviceIds.length }} screen{{ selectedIds.length - skippedDeviceIds.length === 1 ? '' : 's' }}
          · {{ toneByPlaylist.size }} playlist{{ toneByPlaylist.size === 1 ? '' : 's' }}
        </p>
      </div>
      <AppAlert v-if="skippedDeviceIds.length" tone="danger">
        {{ skippedDeviceIds.length }} screen{{ skippedDeviceIds.length === 1 ? '' : 's' }} skipped
      </AppAlert>
      <div class="flex gap-2">
        <AppButton
          variant="secondary" size="sm"
          @click="router.push({ name: 'campaign-detail', params: { id: deployedId } })"
        >
          View campaign
        </AppButton>
        <AppButton size="sm" @click="router.push({ name: 'now' })">Now</AppButton>
      </div>
    </div>

    <template v-else>
      <StepIndicator :steps="STEPS" :current="step" @select="step = $event" />

      <!-- 1. Screens -->
      <section v-if="step === 0" class="flex flex-col gap-4">
        <AppAlert v-if="devicesError" tone="danger">{{ devicesError }}</AppAlert>
        <p v-if="devicesLoading && !devices.length" class="text-sm text-ink-muted">Loading…</p>

        <EmptyState v-else-if="!devices.length" title="No screens yet" description="Add a screen to deploy to.">
          <template #actions>
            <AppButton size="sm" @click="pairing = true"><IconAdd class="size-4" />Add screen</AppButton>
          </template>
        </EmptyState>

        <template v-else>
          <div class="flex items-center justify-between">
            <button
              v-if="availableDevices.length"
              type="button" class="text-[13px] text-ink-muted hover:text-ink" @click="toggleAll"
            >
              {{ allSelected ? 'Clear' : 'Select all' }}
            </button>
            <span v-else />
            <div class="flex items-center gap-3">
              <span class="text-[13px] tabular-nums text-ink-muted">{{ selectedIds.length }} / {{ availableDevices.length }}</span>
              <AppButton variant="ghost" size="sm" @click="pairing = true"><IconAdd class="size-4" />Add screen</AppButton>
            </div>
          </div>

          <div class="grid gap-2 sm:grid-cols-2">
            <button
              v-for="d in orderedDevices"
              :key="d.id"
              type="button"
              class="flex items-center gap-3 rounded-xl p-4 text-left transition-colors duration-200
                     ease-[cubic-bezier(0.4,0,0.2,1)]"
              :class="[
                isSelected(d.id) ? 'bg-raised ring-2 ring-ink ring-inset' : 'bg-surface enabled:hover:bg-raised',
                campaignByDevice.has(d.id) && 'cursor-not-allowed opacity-40',
              ]"
              :disabled="campaignByDevice.has(d.id)"
              :aria-pressed="isSelected(d.id)"
              @click="toggleDevice(d.id)"
            >
              <span
                class="flex size-5 shrink-0 items-center justify-center rounded-full border-2 transition-colors duration-150"
                :class="isSelected(d.id) ? 'border-ink bg-ink text-ink-inverse' : 'border-line-strong'"
              >
                <IconCheck v-if="isSelected(d.id)" class="size-3.5" />
              </span>
              <span class="min-w-0 flex-1">
                <span class="block truncate text-sm text-ink">{{ d.name || 'Unnamed screen' }}</span>
                <span v-if="d.location" class="block truncate text-[12px] text-ink-subtle">{{ d.location }}</span>
                <span v-if="campaignByDevice.has(d.id)" class="block truncate text-[12px] text-ink-muted">
                  Used in {{ campaignByDevice.get(d.id) }}
                </span>
              </span>
              <StatusDot :last-seen-at="d.last_seen_at" />
            </button>
          </div>
        </template>
      </section>

      <!-- 2. Schedule -->
      <section v-else-if="step === 1" class="flex flex-col gap-5">
        <div class="flex flex-col gap-1.5">
          <div class="grid grid-cols-2 gap-3 sm:max-w-md">
            <label class="flex min-w-0 flex-col gap-1.5">
              <span class="text-[13px] text-ink-muted">From</span>
              <input v-model="fromDate" type="date" :class="[DATE_INPUT, dateError ? 'border-danger' : 'border-line-strong']" />
            </label>
            <label class="flex min-w-0 flex-col gap-1.5">
              <span class="text-[13px] text-ink-muted">Until</span>
              <input
                v-model="untilDate" type="date" :min="fromDate || today"
                :class="[DATE_INPUT, dateError ? 'border-danger' : 'border-line-strong']"
              />
            </label>
          </div>
          <p v-if="dateError" class="text-[13px] text-danger">{{ dateError }}</p>
        </div>

        <AppCard><WeekTimeline :slots="timelineSlots" /></AppCard>

        <ul class="flex flex-col gap-2">
          <li v-for="(s, i) in slots" :key="s.key">
            <AppCard>
              <div class="flex items-center gap-2">
                <span class="flex size-6 shrink-0 items-center justify-center rounded-full bg-raised text-[12px] text-ink-muted">
                  {{ i + 1 }}
                </span>
                <PlaylistPicker
                  v-model="s.playlist_id"
                  class="min-w-0 flex-1"
                  :playlists="playlists"
                  :invalid="attempted && !s.playlist_id"
                  @create="composing = { slotKey: s.key, playlist: null }"
                />
                <button
                  v-if="playlistById.get(s.playlist_id)"
                  type="button"
                  class="flex size-9 shrink-0 items-center justify-center rounded-full text-ink-muted
                         transition-colors duration-150 hover:bg-raised hover:text-ink"
                  title="Add media"
                  aria-label="Add media"
                  @click="composing = { slotKey: s.key, playlist: playlistById.get(s.playlist_id) ?? null }"
                >
                  <IconAddPhoto class="size-5" />
                </button>
                <button
                  v-if="slots.length > 1"
                  type="button"
                  class="flex size-9 shrink-0 items-center justify-center rounded-full text-ink-subtle
                         transition-colors duration-150 hover:bg-raised hover:text-ink"
                  aria-label="Remove"
                  @click="slots.splice(i, 1)"
                >
                  <IconClose class="size-4" />
                </button>
              </div>

              <div class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-3 sm:pl-8">
                <div class="flex items-center gap-3">
                  <label class="flex shrink-0 cursor-pointer items-center gap-2">
                    <span class="text-[13px] text-ink-muted">All day</span>
                    <AppSwitch v-model="s.all_day" />
                  </label>
                  <div
                    class="flex items-center gap-1.5 transition-opacity duration-200"
                    :class="s.all_day && 'opacity-40'"
                  >
                    <input
                      v-model="s.starts_at" type="time" aria-label="Start" :disabled="s.all_day"
                      :class="[TIME_INPUT, slotErrors[i] && !s.all_day ? 'border-danger' : 'border-line-strong']"
                    />
                    <span class="text-ink-subtle">–</span>
                    <input
                      v-model="s.ends_at" type="time" aria-label="End" :disabled="s.all_day"
                      :class="[TIME_INPUT, slotErrors[i] && !s.all_day ? 'border-danger' : 'border-line-strong']"
                    />
                    <span v-if="!s.all_day && crossesMidnight(s)" class="text-[11px] text-ink-subtle" title="Ends the next day">+1</span>
                  </div>
                </div>

                <div class="flex gap-0.5 sm:ml-auto">
                  <button
                    v-for="d in DAY_BITS"
                    :key="d.bit"
                    type="button"
                    class="size-7 rounded-full text-[11px] transition-colors duration-150"
                    :class="s.days_of_week & d.bit ? 'bg-ink text-ink-inverse' : 'text-ink-muted hover:bg-raised'"
                    :title="d.short"
                    :aria-pressed="!!(s.days_of_week & d.bit)"
                    @click="s.days_of_week ^= d.bit"
                  >
                    {{ d.short[0] }}
                  </button>
                </div>
              </div>
              <p v-if="shownError(i)" class="mt-2 text-[13px] text-danger sm:pl-8">{{ shownError(i) }}</p>
            </AppCard>
          </li>
        </ul>

        <AppButton variant="secondary" size="sm" class="self-start" @click="addSlot">
          <IconAdd class="size-4" />Add playlist
        </AppButton>
      </section>

      <!-- 3. Review -->
      <section v-else class="flex flex-col gap-8">
        <div class="sm:max-w-md">
          <AppInput id="deploy-name" v-model="campaignName" label="Name" required />
        </div>

        <div class="flex flex-col gap-3">
          <h2 class="text-lg">Screens <span class="text-ink-subtle">{{ selectedDevices.length }}</span></h2>
          <div class="flex flex-wrap gap-2">
            <span v-for="d in selectedDevices" :key="d.id" class="rounded-full bg-surface px-3 py-1 text-[13px] text-ink">
              {{ d.name || 'Unnamed screen' }}<span v-if="d.location" class="text-ink-subtle"> · {{ d.location }}</span>
            </span>
          </div>
        </div>

        <div class="flex flex-col gap-3">
          <div class="flex items-baseline justify-between gap-4">
            <h2 class="text-lg">Schedule</h2>
            <span class="text-[13px] text-ink-muted">{{ dateSummary }}</span>
          </div>
          <AppCard><WeekTimeline :slots="timelineSlots" /></AppCard>
          <ul class="flex flex-col divide-y divide-line overflow-hidden rounded-xl bg-surface">
            <li v-for="s in sortedSlots" :key="s.key" class="flex items-center gap-3 px-4 py-3">
              <div class="h-9 w-16 shrink-0 overflow-hidden rounded-md bg-raised">
                <img
                  v-if="playlistById.get(s.playlist_id)?.thumbnails[0]"
                  :src="playlistById.get(s.playlist_id)?.thumbnails[0] ?? ''"
                  class="size-full object-cover"
                />
              </div>
              <span class="min-w-0 flex-1 truncate text-sm text-ink">{{ playlistById.get(s.playlist_id)?.name }}</span>
              <span class="hidden text-[13px] text-ink-muted sm:inline">{{ dayLabel(s.days_of_week) }}</span>
              <span v-if="s.all_day" class="shrink-0 text-[13px] text-ink">All day</span>
              <span v-else class="shrink-0 text-[13px] tabular-nums text-ink">
                {{ s.starts_at }}–{{ s.ends_at }}<span v-if="crossesMidnight(s)" class="text-ink-subtle"> +1</span>
              </span>
            </li>
          </ul>
        </div>

        <AppAlert v-for="d in devicesWithDefault" :key="d.id">
          {{ d.name }} fills gaps with {{ playlistById.get(d.playlist_id ?? '')?.name ?? 'its default playlist' }}
        </AppAlert>
        <AppAlert v-if="saveError" tone="danger">{{ saveError }}</AppAlert>
      </section>

      <div class="flex items-center justify-between border-t border-line pt-6">
        <AppButton v-if="step > 0" variant="ghost" size="sm" @click="step--">
          <IconArrowBack class="size-4" />Back
        </AppButton>
        <span v-else />
        <AppButton v-if="step < STEPS.length - 1" :disabled="step === 0 && !selectedIds.length" @click="next">
          Next<IconArrowForward class="size-4" />
        </AppButton>
        <AppButton v-else :disabled="!campaignName.trim()" :loading="deploying" @click="onDeploy">
          <IconRocket class="size-4" />Deploy
        </AppButton>
      </div>
    </template>

    <AppModal v-if="pairing" title="Add a screen" @close="pairing = false">
      <PairScreenForm
        :is-saving="claiming" :claim-error="claimError" :connecting="connecting"
        @submit="onClaim" @cancel="pairing = false"
      />
    </AppModal>

    <PlaylistComposeContainer
      v-if="composing"
      :playlist="composing.playlist"
      @saved="onComposed"
      @close="composing = null"
    />
  </div>
</template>
