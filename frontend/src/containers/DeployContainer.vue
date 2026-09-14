<script setup lang="ts">
/**
 * Creating and editing a campaign: screens → schedule → review, saved as one `CampaignWrite`.
 * `/deploy` creates; `/campaigns/:id` loads that campaign into the same three steps. Every rule
 * shares one date range, and rules on one campaign may not overlap, so what the timeline shows
 * is exactly what plays: each window its playlist, everything else asleep.
 */
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
import DeviceCard from '@/reusables/DeviceCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import PairScreenForm from '@/reusables/PairScreenForm.vue'
import PlaylistPicker from '@/reusables/PlaylistPicker.vue'
import StepIndicator from '@/reusables/StepIndicator.vue'
import WeekTimeline from '@/reusables/WeekTimeline.vue'
import { ALL_DAYS, DAY_BITS, WEEKDAYS, WEEKENDS } from '@/types/api'
import type { CampaignRuleRead, ClaimBody, PlaylistSummary } from '@/types/api'
import { crossesMidnight, toMinutes, windowLength, windowsOverlap } from '@/utils/scheduleMath'
import type { TimelineSlot, TimeWindow } from '@/utils/scheduleMath'

const route = useRoute()
const router = useRouter()

/** Present on /campaigns/:id — that alone is what puts this flow in edit mode. */
const campaignId = typeof route.params.id === 'string' ? route.params.id : null
const isEdit = campaignId !== null

const {
  campaign, isLoading: campaignLoading, error: campaignError,
  isSaving, isDeleting, saveError, skippedDeviceIds, save, remove,
} = useCampaignDetail(campaignId)

const STEPS = ['Screens', 'Schedule', 'Review']
const step = ref(0)
/** The furthest step reached — every step up to it stays clickable. Editing starts with all of
 *  them reachable, since a saved campaign is already complete. */
const furthest = ref(isEdit ? STEPS.length - 1 : 0)

// --- 1. Screens ---

const {
  items: devices, resolved, isLoading: devicesLoading, error: devicesError,
  isSaving: claiming, claimError, connecting, claim,
} = useDevices()

/** Same "currently playing" line the Devices list shows, so a screen's card reads identically
 *  in both places. */
function nowPlaying(deviceId: string): { text: string; via: string | null } {
  const r = resolved.value.get(deviceId)
  if (!r?.playlist_id) return { text: 'No playlist', via: null }
  return {
    text: playlistById.value.get(r.playlist_id)?.name ?? '—',
    via: r.schedule_name ? `via “${r.schedule_name}”` : null,
  }
}

const { items: campaigns } = useCampaigns()
/** Screens already in *another* campaign aren't offered: two campaigns on one screen resolve by
 *  priority, which this flow deliberately never asks about. Keyed to that campaign's name so the
 *  card can say where the screen is used. A screen this campaign already holds always stays
 *  pickable, even if older data also put it in another one — editing must not silently drop it. */
const campaignByDevice = computed(() => {
  const own = new Set(campaign.value?.device_ids ?? [])
  const map = new Map<string, string>()
  for (const c of campaigns.value) {
    if (c.id === campaignId) continue
    for (const id of c.device_ids) if (!own.has(id) && !map.has(id)) map.set(id, c.name)
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
  /** Not editable here, but carried through untouched: a campaign made with the older editor
   *  may have named or prioritised rules, and saving it from this flow must not erase them. */
  name: string
  priority: number
}

/** The backend has no 24:00 and rejects start == end, so a whole day is spelled 00:00–23:59. */
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
  return {
    key: crypto.randomUUID(), playlist_id: '', starts_at, ends_at, days_of_week: ALL_DAYS,
    all_day: false, name: '', priority: 0,
  }
}

const slots = ref<Slot[]>([newSlot('09:00', '17:00')])
const fromDate = ref('')
const untilDate = ref('')
/** Optional, and only sent alongside its date — a time with no date has nothing to narrow. */
const fromTime = ref('')
const untilTime = ref('')
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
/** `YYYY-MM-DDTHH:MM` sorts as text, so bounds compare without parsing. A missing time is the
 *  start (00:00) or the end (24:00) of that day — the same way the backend reads a bare date. */
const bound = (date: string, time: string, fallback: string) => `${date}T${time || fallback}`
function nowStamp(): string {
  const d = new Date()
  return `${localIsoDate(d)}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
const dateError = computed(() => {
  const start = fromDate.value ? bound(fromDate.value, fromTime.value, '00:00') : ''
  const end = untilDate.value ? bound(untilDate.value, untilTime.value, '24:00') : ''
  if (start && end && end <= start) return "Can't end before it starts"
  if (end && end <= nowStamp()) return 'Already ended'
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

const campaignName = ref('')
const savedId = ref<string | null>(null)

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
const withTime = (date: string, time: string) => (time ? `${formatDate(date)}, ${time}` : formatDate(date))
const dateSummary = computed(() => {
  const from = fromDate.value ? withTime(fromDate.value, fromTime.value) : ''
  const until = untilDate.value ? withTime(untilDate.value, untilTime.value) : ''
  if (from && until) return `${from} – ${until}`
  if (from) return `From ${from}`
  if (until) return `Until ${until}`
  return 'Ongoing'
})
function dayLabel(mask: number): string {
  if (mask === ALL_DAYS) return 'Every day'
  if (mask === WEEKDAYS) return 'Weekdays'
  if (mask === WEEKENDS) return 'Weekends'
  return DAY_BITS.filter((d) => mask & d.bit).map((d) => d.short).join(', ')
}

async function onSave() {
  savedId.value = await save({
    name: campaignName.value.trim(),
    device_ids: selectedIds.value,
    rules: slots.value.map((s) => {
      const w = effective(s)
      return {
        playlist_id: s.playlist_id,
        name: s.name,
        priority: s.priority,
        days_of_week: w.days_of_week,
        starts_at: `${w.starts_at}:00`,
        ends_at: `${w.ends_at}:00`,
        start_date: fromDate.value || null,
        end_date: untilDate.value || null,
        start_time: fromDate.value && fromTime.value ? `${fromTime.value}:00` : null,
        end_time: untilDate.value && untilTime.value ? `${untilTime.value}:00` : null,
      }
    }),
  })
}

const confirmingDelete = ref(false)
async function onDelete() {
  if (await remove()) router.push({ name: 'campaigns' })
  else confirmingDelete.value = false
}

// --- Editing: load the saved campaign into the steps above ---

/** The older editor allowed a date range per rule; this flow has one for the whole campaign.
 *  When a loaded campaign's rules disagree, the first rule's range is shown and saving applies
 *  it to all of them — said out loud rather than done silently. */
const mixedRanges = ref(false)
/** True once the form holds real state — from a restored draft or the loaded campaign — so the
 *  campaign never overwrites what someone was in the middle of. */
let hydrated = false

// --- Detour: making a playlist on the Playlists page, then coming back ---

/**
 * "New playlist" sends people to the real Playlists page and editor rather than a cut-down
 * modal. Everything entered so far is parked in this tab's sessionStorage on the way out and
 * restored on the way back — with the new playlist dropped into the row that asked for it. The
 * Playlists page and editor bring people back here with `?playlist=<id>` after saving, or
 * `?returned=1` if they back out.
 */
const DRAFT_KEY = `deploy-draft:${route.path}`

interface DeployDraft {
  step: number
  furthest: number
  selectedIds: string[]
  slots: Slot[]
  fromDate: string
  untilDate: string
  fromTime: string
  untilTime: string
  campaignName: string
  attempted: boolean
  mixedRanges: boolean
  pendingSlot: string
}

function startNewPlaylist(slotKey: string) {
  const draft: DeployDraft = {
    step: step.value, furthest: furthest.value, selectedIds: selectedIds.value, slots: slots.value,
    fromDate: fromDate.value, untilDate: untilDate.value, fromTime: fromTime.value, untilTime: untilTime.value,
    campaignName: campaignName.value, attempted: attempted.value, mixedRanges: mixedRanges.value,
    pendingSlot: slotKey,
  }
  try {
    sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft))
  } catch {
    // Storage blocked (private mode, a locked-down browser): the detour still works, the
    // draft just isn't kept.
  }
  router.push({ name: 'playlists', query: { new: '1', returnTo: route.path } })
}

/** Always taken out of storage, used or not — a detour someone abandoned must not resurface
 *  the next time they happen to open this page. */
function takeDraft(): DeployDraft | null {
  try {
    const raw = sessionStorage.getItem(DRAFT_KEY)
    sessionStorage.removeItem(DRAFT_KEY)
    return raw ? (JSON.parse(raw) as DeployDraft) : null
  } catch {
    return null
  }
}

const returning = 'playlist' in route.query || 'returned' in route.query
const restored = takeDraft()
if (returning && restored) {
  hydrated = true
  step.value = restored.step
  furthest.value = restored.furthest
  selectedIds.value = restored.selectedIds
  slots.value = restored.slots
  fromDate.value = restored.fromDate
  untilDate.value = restored.untilDate
  fromTime.value = restored.fromTime
  untilTime.value = restored.untilTime
  campaignName.value = restored.campaignName
  attempted.value = restored.attempted
  mixedRanges.value = restored.mixedRanges
  const created = typeof route.query.playlist === 'string' ? route.query.playlist : null
  const slot = slots.value.find((s) => s.key === restored.pendingSlot)
  if (created && slot) slot.playlist_id = created
}
// Drop the return marker so a reload doesn't try to restore a draft that's already gone.
if (returning) router.replace({ path: route.path })

watch(campaign, (c) => {
  // Once only: saving writes the result back into `campaign`, which must not reset the form.
  if (!c || hydrated) return
  hydrated = true
  campaignName.value = c.name
  selectedIds.value = [...c.device_ids]
  if (!c.rules.length) return

  slots.value = c.rules.map((r): Slot => {
    const starts = r.starts_at.slice(0, 5)
    const ends = r.ends_at.slice(0, 5)
    const allDay = starts === ALL_DAY.starts_at && ends === ALL_DAY.ends_at
    return {
      key: crypto.randomUUID(), playlist_id: r.playlist_id, days_of_week: r.days_of_week,
      starts_at: allDay ? '09:00' : starts, ends_at: allDay ? '17:00' : ends, all_day: allDay,
      name: r.name, priority: r.priority,
    }
  })
  const first = c.rules[0]
  fromDate.value = first.start_date ?? ''
  untilDate.value = first.end_date ?? ''
  fromTime.value = first.start_time?.slice(0, 5) ?? ''
  untilTime.value = first.end_time?.slice(0, 5) ?? ''
  const range = (r: CampaignRuleRead) => [r.start_date, r.end_date, r.start_time, r.end_time].join('|')
  mixedRanges.value = c.rules.some((r) => range(r) !== range(first))
}, { immediate: true })

// --- Navigation ---

/** One step forward if the current step is complete; false, with its errors showing, if not. */
function advance(): boolean {
  if (step.value === 0 && !selectedIds.value.length) return false
  if (step.value === 1) {
    attempted.value = true
    if (!scheduleValid.value) return false
    if (!campaignName.value) {
      campaignName.value = `Deployment · ${new Date().toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}`
    }
  }
  step.value++
  furthest.value = Math.max(furthest.value, step.value)
  return true
}

/** Back is always free; forward walks through each step in between, so jumping ahead can't
 *  skip past a step that isn't valid. */
function goTo(target: number) {
  if (target <= step.value) {
    step.value = target
    return
  }
  while (step.value < target && advance()) { /* advance() moves the step */ }
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
const BOUND_TIME_INPUT =
  'h-10 w-full min-w-0 appearance-none rounded-lg border bg-canvas px-2 text-center text-sm tabular-nums text-ink ' +
  'transition-opacity duration-200 focus:border-ink focus:outline-none disabled:cursor-not-allowed disabled:opacity-40'
</script>

<template>
  <div class="flex flex-col gap-8">
    <div class="flex flex-col gap-4">
      <AppButton v-if="isEdit" variant="ghost" size="sm" class="self-start" @click="router.push({ name: 'campaigns' })">
        <IconArrowBack class="size-4" />Campaigns
      </AppButton>
      <PageTitle :title="isEdit ? (campaign?.name || 'Campaign') : 'Deploy'">
        <template v-if="isEdit && campaign && !savedId" #actions>
          <AppButton variant="danger" size="sm" @click="confirmingDelete = true">Delete</AppButton>
        </template>
      </PageTitle>
    </div>

    <p v-if="campaignLoading" class="text-sm text-ink-muted">Loading…</p>
    <AppAlert v-else-if="campaignError" tone="danger">{{ campaignError }}</AppAlert>

    <!-- Done -->
    <div v-else-if="savedId" class="flex flex-col items-center gap-4 rounded-xl bg-surface px-6 py-16 text-center">
      <span class="flex size-14 items-center justify-center rounded-full bg-ink text-ink-inverse">
        <IconCheck class="size-7" />
      </span>
      <div>
        <h2 class="text-2xl">{{ isEdit ? 'Saved' : 'Deployed' }}</h2>
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
          v-if="isEdit"
          variant="secondary" size="sm"
          @click="router.push({ name: 'campaigns' })"
        >
          Campaigns
        </AppButton>
        <AppButton
          v-else
          variant="secondary" size="sm"
          @click="router.push({ name: 'campaign-detail', params: { id: savedId } })"
        >
          View campaign
        </AppButton>
        <AppButton size="sm" @click="router.push({ name: 'now' })">Now</AppButton>
      </div>
    </div>

    <template v-else>
      <StepIndicator :steps="STEPS" :current="step" :reachable="furthest" @select="goTo" />

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

          <!-- The Devices list's own card, in picker mode — the only difference is selecting. -->
          <div class="flex flex-col gap-2">
            <DeviceCard
              v-for="d in orderedDevices"
              :key="d.id"
              :device="d"
              :playing="nowPlaying(d.id).text"
              :via="nowPlaying(d.id).via"
              selectable
              :selected="isSelected(d.id)"
              :disabled="campaignByDevice.has(d.id)"
              :note="campaignByDevice.has(d.id) ? `Used in ${campaignByDevice.get(d.id)}` : null"
              @click="toggleDevice(d.id)"
            />
          </div>
        </template>
      </section>

      <!-- 2. Schedule -->
      <section v-else-if="step === 1" class="flex flex-col gap-5">
        <AppAlert v-if="mixedRanges">
          This campaign's rules had different dates — saving applies these to all of them.
        </AppAlert>

        <div class="flex flex-col gap-1.5">
          <div class="grid gap-3 sm:max-w-2xl sm:grid-cols-2">
            <div class="flex min-w-0 flex-col gap-1.5">
              <span class="text-[13px] text-ink-muted">From</span>
              <div class="grid grid-cols-[minmax(0,1fr)_6.5rem] gap-2">
                <input
                  v-model="fromDate" type="date" aria-label="From date"
                  :class="[DATE_INPUT, dateError ? 'border-danger' : 'border-line-strong']"
                />
                <input
                  v-model="fromTime" type="time" aria-label="From time" :disabled="!fromDate"
                  :class="[BOUND_TIME_INPUT, dateError ? 'border-danger' : 'border-line-strong']"
                />
              </div>
            </div>
            <div class="flex min-w-0 flex-col gap-1.5">
              <span class="text-[13px] text-ink-muted">Until</span>
              <div class="grid grid-cols-[minmax(0,1fr)_6.5rem] gap-2">
                <input
                  v-model="untilDate" type="date" aria-label="Until date" :min="fromDate || today"
                  :class="[DATE_INPUT, dateError ? 'border-danger' : 'border-line-strong']"
                />
                <input
                  v-model="untilTime" type="time" aria-label="Until time" :disabled="!untilDate"
                  :class="[BOUND_TIME_INPUT, dateError ? 'border-danger' : 'border-line-strong']"
                />
              </div>
            </div>
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
                  @create="startNewPlaylist(s.key)"
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
        <AppButton v-if="step < STEPS.length - 1" :disabled="step === 0 && !selectedIds.length" @click="advance">
          Next<IconArrowForward class="size-4" />
        </AppButton>
        <AppButton v-else :disabled="!campaignName.trim()" :loading="isSaving" @click="onSave">
          <template v-if="isEdit"><IconCheck class="size-4" />Save changes</template>
          <template v-else><IconRocket class="size-4" />Deploy</template>
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

    <AppModal v-if="confirmingDelete" title="Delete this campaign?" @close="confirmingDelete = false">
      <p class="text-sm text-ink-muted">Its screens go back to their defaults for the times it covered.</p>
      <div class="mt-4 flex justify-end gap-2">
        <AppButton variant="secondary" size="sm" @click="confirmingDelete = false">Cancel</AppButton>
        <AppButton variant="danger" size="sm" :loading="isDeleting" @click="onDelete">Delete</AppButton>
      </div>
    </AppModal>
  </div>
</template>
