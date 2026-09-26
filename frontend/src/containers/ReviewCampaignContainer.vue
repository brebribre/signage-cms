<script setup lang="ts">
/**
 * A campaign change, shown so it can be judged before it reaches a screen: when each playlist
 * plays across the week, which screens it reaches, and — pick a rule — what that rule's
 * playlist actually looks like on a screen, scene by scene.
 *
 * Before and After, as a playlist review has: After (what was sent) opens first, since it is
 * what needs judging; Before is the campaign as saved now. A new campaign has only After, and a
 * removal only the campaign being removed. On a change, rules that are new or gone are marked,
 * and the screens it gains or loses are listed, so what moved is plain without comparing by eye.
 */
import { computed, ref, watch } from 'vue'
import IconLanguage from '~icons/material-symbols/language'
import IconText from '~icons/material-symbols/text-fields'
import IconTv from '~icons/material-symbols/tv-outline'

import type { CampaignSide, RulePlaylist } from '@/hooks/useReviewDetail'
import type { DraftItem } from '@/hooks/usePlaylistEditor'
import { usePlaylistPreview } from '@/hooks/usePlaylistPreview'
import AppTabs from '@/reusables/AppTabs.vue'
import ReviewPreviewPanel from '@/reusables/ReviewPreviewPanel.vue'
import WeekTimeline from '@/reusables/WeekTimeline.vue'
import type { CampaignRuleWrite, DeviceRead, ReviewKind } from '@/types/api'
import { timelineTone } from '@/utils/scheduleMath'
import type { TimelineSlot } from '@/utils/scheduleMath'
import type { PreviewScreen } from '@/utils/reviewScreens'

const props = defineProps<{
  kind: ReviewKind
  before: CampaignSide | null
  after: CampaignSide | null
  playlists: Map<string, RulePlaylist>
  devices: DeviceRead[]
  /** The screens the change reaches, as saved on the review: what the preview offers, and the
   *  names of screens deleted since. */
  screens: PreviewScreen[]
}>()

// --- Which side ---

type Side = 'before' | 'after'
const side = ref<Side>(props.after ? 'after' : 'before')
const tabs = computed(() => [
  ...(props.before ? [{ value: 'before', label: props.kind === 'campaign_delete' ? 'Being removed' : 'Before', badge: props.before.rules.length }] : []),
  ...(props.after ? [{ value: 'after', label: 'After', badge: props.after.rules.length }] : []),
])
const shown = computed(() => (side.value === 'before' ? props.before : props.after))

// --- Rules, and what changed between the two sides ---

const hhmm = (t: string | null | undefined) => (t ? t.slice(0, 5) : '')
/** A rule as a comparable string: two rules are "the same" when every setting matches. */
function signature(r: CampaignRuleWrite): string {
  return JSON.stringify([
    r.playlist_id, r.name ?? '', r.days_of_week ?? 0b1111111, hhmm(r.starts_at), hhmm(r.ends_at),
    r.priority ?? 0, r.start_date ?? null, r.end_date ?? null, hhmm(r.start_time), hhmm(r.end_time),
  ])
}
const isChange = computed(() => props.kind === 'campaign_update' && !!props.before && !!props.after)
/** How a rule differs from the other side. A rule with the same playlist and name on both sides
 *  is the same rule edited ("Changed"); one with no counterpart was added ("New", on After) or
 *  dropped ("Removed", on Before). Identical rules carry no mark. */
function ruleMark(r: CampaignRuleWrite): 'New' | 'Changed' | 'Removed' | null {
  if (!isChange.value) return null
  const other = side.value === 'after' ? props.before! : props.after!
  if (other.rules.some((o) => signature(o) === signature(r))) return null
  const sameRule = (o: CampaignRuleWrite) => o.playlist_id === r.playlist_id && (o.name ?? '') === (r.name ?? '')
  if (other.rules.some(sameRule)) return 'Changed'
  return side.value === 'after' ? 'New' : 'Removed'
}
const MARK_CLASS = {
  New: 'bg-emerald-50 text-emerald-700',
  Changed: 'bg-amber-50 text-amber-700',
  Removed: 'bg-raised text-danger',
} as const

/** One colour per playlist, the same on both sides and on the timeline, so a playlist is
 *  recognisable at a glance wherever it appears. */
const toneOf = computed(() => {
  const ids = [...(props.before?.rules ?? []), ...(props.after?.rules ?? [])].map((r) => r.playlist_id)
  return new Map([...new Set(ids)].map((id, i) => [id, i]))
})
function playlistName(id: string): string {
  return props.playlists.get(id)?.name ?? 'A playlist that is no longer here'
}

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
function daysLabel(mask: number | undefined): string {
  const m = mask ?? 0b1111111
  if (m === 0b1111111) return 'Every day'
  if (m === 0b0011111) return 'Weekdays'
  if (m === 0b1100000) return 'Weekends'
  return DAYS.filter((_, i) => m & (1 << i)).join(', ')
}
function whenLabel(r: CampaignRuleWrite): string {
  const parts = [daysLabel(r.days_of_week), `${hhmm(r.starts_at)}–${hhmm(r.ends_at)}`]
  if (r.priority) parts.push(`priority ${r.priority}`)
  if (r.start_date || r.end_date) parts.push(`${r.start_date ?? '…'} to ${r.end_date ?? '…'}`)
  return parts.join(' · ')
}

const slots = computed<TimelineSlot[]>(() =>
  (shown.value?.rules ?? []).map((r, i) => ({
    key: `${side.value}-${i}`,
    label: playlistName(r.playlist_id),
    tone: toneOf.value.get(r.playlist_id) ?? 0,
    starts_at: hhmm(r.starts_at),
    ends_at: hhmm(r.ends_at),
    days_of_week: r.days_of_week ?? 0b1111111,
  })),
)

// --- Screens it reaches, and on a change, which it gains or loses ---

const deviceName = (id: string) =>
  props.devices.find((d) => d.id === id)?.name ?? props.screens.find((s) => s.id === id)?.name ?? 'A screen you can’t see'
const screenNames = computed(() => (shown.value?.device_ids ?? []).map(deviceName))
const gained = computed(() =>
  isChange.value ? props.after!.device_ids.filter((id) => !props.before!.device_ids.includes(id)).map(deviceName) : [],
)
const lost = computed(() =>
  isChange.value ? props.before!.device_ids.filter((id) => !props.after!.device_ids.includes(id)).map(deviceName) : [],
)

// --- The preview: the picked rule's playlist, playing ---

const ruleIndex = ref(0)
const rule = computed(() => shown.value?.rules[ruleIndex.value] ?? null)
const scenes = computed<DraftItem[]>(() => (rule.value ? props.playlists.get(rule.value.playlist_id)?.scenes ?? [] : []))
const preview = usePlaylistPreview(() => scenes.value)

watch(side, () => (ruleIndex.value = 0))
watch(scenes, (list) => {
  const first = list.find((s) => s.isEnabled)
  if (first) preview.select(first)
})

function sceneThumb(item: DraftItem): string | null {
  return item.elements.find((e) => e.thumbnailUrl)?.thumbnailUrl ?? null
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <AppTabs v-if="tabs.length > 1" :items="tabs" :model-value="side" @update:model-value="side = $event as Side" />
    <p v-if="kind === 'campaign_update' && !before" class="-mt-2 text-[13px] text-ink-subtle">
      The campaign this changes no longer exists, so there is no Before.
    </p>
    <p v-else-if="kind === 'campaign_delete'" class="rounded-xl bg-surface p-3 text-sm text-ink">
      Approving removes this campaign from every screen it is on. Those screens fall back to whatever
      else is scheduled, or their default playlist.
    </p>

    <template v-if="shown">
      <!-- What moved, said once, above the detail. -->
      <div v-if="isChange && (gained.length || lost.length)" class="flex flex-wrap gap-2 text-[13px]">
        <span v-for="n in gained" :key="`+${n}`" class="rounded-full bg-emerald-50 px-2.5 py-0.5 text-emerald-700">+ {{ n }}</span>
        <span v-for="n in lost" :key="`-${n}`" class="rounded-full bg-raised px-2.5 py-0.5 text-danger">− {{ n }}</span>
      </div>

      <!-- When it plays -->
      <section class="rounded-xl bg-surface p-4" aria-labelledby="campaign-week">
        <div class="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <h3 id="campaign-week" class="text-sm text-ink">When it plays</h3>
          <p class="flex items-center gap-1.5 text-[12px] text-ink-muted">
            <IconTv class="size-3.5" aria-hidden="true" />
            {{ screenNames.length }} screen{{ screenNames.length === 1 ? '' : 's' }}<template v-if="screenNames.length">: {{ screenNames.slice(0, 3).join(', ') }}<template v-if="screenNames.length > 3"> +{{ screenNames.length - 3 }}</template></template>
          </p>
        </div>
        <WeekTimeline :slots="slots" />
      </section>

      <!-- The rules, and the picked one's playlist on a screen -->
      <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div class="flex flex-col gap-2">
          <p class="text-sm text-ink-muted">Playlists, in priority order · pick one to preview it</p>
          <button
            v-for="(r, i) in shown.rules"
            :key="`${side}-${i}`"
            type="button"
            class="flex items-start gap-3 rounded-xl bg-surface p-3 text-left transition-colors duration-200 hover:bg-raised
                   focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-bright"
            :class="ruleIndex === i && 'bg-raised ring-2 ring-ink'"
            :aria-pressed="ruleIndex === i"
            @click="ruleIndex = i"
          >
            <span class="mt-1 size-3 shrink-0" :style="{ background: timelineTone(toneOf.get(r.playlist_id) ?? 0) }" aria-hidden="true" />
            <span class="min-w-0 flex-1">
              <span class="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-ink">
                <span class="truncate">{{ playlistName(r.playlist_id) }}</span>
                <span v-if="r.name" class="truncate text-ink-muted">· {{ r.name }}</span>
                <span
                  v-if="ruleMark(r)"
                  class="rounded-full px-2 py-px text-[11px]"
                  :class="MARK_CLASS[ruleMark(r)!]"
                >{{ ruleMark(r) }}</span>
              </span>
              <span class="mt-0.5 block text-[13px] text-ink-muted">{{ whenLabel(r) }}</span>
            </span>
          </button>
          <p v-if="!shown.rules.length" class="text-[13px] text-ink-muted">No playlists.</p>
        </div>

        <ReviewPreviewPanel :preview="preview" :screens="screens">
          <p v-if="rule && !playlists.get(rule.playlist_id)?.scenes" class="text-[13px] text-ink-muted">
            This playlist couldn’t be loaded — it may have been deleted since the change was sent.
          </p>
          <template v-else-if="scenes.length">
            <p class="text-[12px] text-ink-muted">
              {{ playlistName(rule!.playlist_id) }} · {{ scenes.length }} scene{{ scenes.length === 1 ? '' : 's' }}
            </p>
            <!-- The playlist's scenes: tap one to show it. -->
            <ul class="flex gap-2 overflow-x-auto pb-1">
              <li v-for="(s, i) in scenes" :key="s.key" class="shrink-0">
                <button
                  type="button"
                  class="flex size-14 items-center justify-center overflow-hidden rounded-md bg-raised transition
                         focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-bright"
                  :class="[preview.current.value?.key === s.key ? 'ring-2 ring-ink' : 'opacity-80 hover:opacity-100', !s.isEnabled && 'opacity-40']"
                  :disabled="!s.isEnabled"
                  :aria-label="`Scene ${i + 1}`"
                  @click="preview.select(s)"
                >
                  <img v-if="sceneThumb(s)" :src="sceneThumb(s)!" alt="" class="size-full object-cover" />
                  <!-- No picture to show: the scene's own colour, and what is on it. -->
                  <span
                    v-else
                    class="flex size-full items-center justify-center"
                    :style="s.background === 'color' && s.backgroundColor ? { background: s.backgroundColor } : undefined"
                  >
                    <component
                      :is="s.elements[0]?.kind === 'web' ? IconLanguage : IconText"
                      class="size-5"
                      :class="s.background === 'color' && s.backgroundColor ? 'text-white/85' : 'text-ink-muted'"
                      aria-hidden="true"
                    />
                  </span>
                </button>
              </li>
            </ul>
          </template>
          <p v-else-if="rule" class="text-[13px] text-ink-muted">This playlist has no scenes yet.</p>
        </ReviewPreviewPanel>
      </div>
    </template>
    <p v-else class="text-[13px] text-ink-muted">There is nothing to show for this campaign.</p>
  </div>
</template>
