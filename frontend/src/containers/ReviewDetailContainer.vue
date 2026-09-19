<script setup lang="ts">
/**
 * One review, opened: the change shown the way the playlist page shows a playlist — the scene
 * list and the screen preview — with the saved playlist a click away for comparison. Read-only:
 * the only things anyone can do here are approve, reject or withdraw. A manager sees exactly
 * this page for their own reviews, minus the owner's buttons.
 */
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import IconArrowBack from '~icons/material-symbols/arrow-back'
import IconCheck from '~icons/material-symbols/check'
import IconClose from '~icons/material-symbols/close'
import IconLanguage from '~icons/material-symbols/language'
import IconPause from '~icons/material-symbols/pause'
import IconPlayArrow from '~icons/material-symbols/play-arrow'
import IconTv from '~icons/material-symbols/tv-outline'

import { useAuth } from '@/hooks/useAuth'
import { useDevices } from '@/hooks/useDevices'
import { useFormat } from '@/hooks/useFormat'
import { useMedia } from '@/hooks/useMedia'
import { usePlaylistPreview } from '@/hooks/usePlaylistPreview'
import { usePlaylists } from '@/hooks/usePlaylists'
import { useReviewDetail } from '@/hooks/useReviewDetail'
import { SCREEN_PRESETS, useScreenPresets } from '@/hooks/useScreenPresets'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppModal from '@/reusables/AppModal.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import ScreenPreview from '@/reusables/ScreenPreview.vue'
import SkeletonBlock from '@/reusables/SkeletonBlock.vue'
import type { DraftItem } from '@/hooks/usePlaylistEditor'
import type { CampaignRuleWrite, ReviewStatus } from '@/types/api'

const route = useRoute()
const router = useRouter()
const id = route.params.id as string

const { isOwner } = useAuth()
const { relativeTime, duration } = useFormat()
const { items: library } = useMedia()
const { items: devices } = useDevices()
const { items: playlists } = usePlaylists()
const { review, proposed, current, currentName, isLoading, error, isActing, actionError, approve, reject, withdraw } =
  useReviewDetail(id, () => library.value)
const { presetId, isCustom, customWidth, customHeight, screen, deviceOptions } = useScreenPresets(devices)

const STATUS: Record<ReviewStatus, { label: string; cls: string }> = {
  pending: { label: 'Waiting', cls: 'bg-brand-soft text-brand' },
  approved: { label: 'Approved', cls: 'bg-emerald-50 text-emerald-700' },
  rejected: { label: 'Rejected', cls: 'bg-raised text-danger' },
  withdrawn: { label: 'Withdrawn', cls: 'bg-raised text-ink-muted' },
}

// --- Playlist changes: Proposed and Current sides, one preview ---
const side = ref<'proposed' | 'current'>('proposed')
const shown = computed<DraftItem[]>(() => (side.value === 'current' ? current.value ?? [] : proposed.value))
const preview = usePlaylistPreview(() => shown.value)
watch(side, () => preview.select(shown.value[0] ?? { key: '' } as DraftItem))

function sceneLabel(item: DraftItem): string {
  if (!item.elements.length) return 'Empty scene'
  const first = item.elements[0].filename
  return item.elements.length > 1 ? `${first} + ${item.elements.length - 1}` : first
}

// --- Campaign changes: the rules, readable ---
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
function daysLabel(mask: number | undefined): string {
  const m = mask ?? 0b1111111
  if (m === 0b1111111) return 'Every day'
  if (m === 0b0011111) return 'Weekdays'
  if (m === 0b1100000) return 'Weekends'
  return DAYS.filter((_, i) => m & (1 << i)).join(', ')
}
const hhmm = (t: string | undefined | null) => (t ? t.slice(0, 5) : '')
function playlistName(playlistId: string): string {
  return playlists.value.find((p) => p.id === playlistId)?.name ?? 'A playlist that is no longer here'
}
const rules = computed(() => ((review.value?.payload.rules as CampaignRuleWrite[] | undefined) ?? []))
const devicePayload = computed(() => review.value?.payload as { playlist_id?: string | null; clear_playlist?: boolean })

// --- Deciding ---
const rejecting = ref(false)
const rejectNote = ref('')
async function confirmReject() {
  if (await reject(rejectNote.value.trim() || undefined)) rejecting.value = false
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <AppButton variant="ghost" size="sm" class="self-start" @click="router.push({ name: 'reviews' })">
      <IconArrowBack class="size-4" />
      Reviews
    </AppButton>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <SkeletonBlock v-else-if="isLoading || !review" class="h-40" />

    <template v-else>
      <PageTitle :title="review.summary">
        <template #actions>
          <div class="flex flex-wrap items-center gap-2">
            <span class="rounded-full px-2.5 py-0.5 text-[12px]" :class="STATUS[review.status].cls">
              {{ STATUS[review.status].label }}
            </span>
            <template v-if="review.status === 'pending' && isOwner">
              <AppButton variant="secondary" size="sm" :disabled="isActing" @click="rejecting = true; rejectNote = ''">
                <IconClose class="size-4" aria-hidden="true" />Reject
              </AppButton>
              <AppButton size="sm" :loading="isActing" @click="approve()">
                <IconCheck class="size-4" aria-hidden="true" />Approve
              </AppButton>
            </template>
            <AppButton v-else-if="review.status === 'pending'" variant="secondary" size="sm" :loading="isActing" @click="withdraw()">
              Withdraw
            </AppButton>
          </div>
        </template>
      </PageTitle>

      <p class="-mt-4 text-[13px] text-ink-muted">
        Sent by {{ review.requested_by_name }} {{ relativeTime(review.created_at) }}<template v-if="review.reviewed_at">
          · decided {{ relativeTime(review.reviewed_at) }}</template>
      </p>
      <AppAlert v-if="review.note">“{{ review.note }}”</AppAlert>
      <AppAlert v-if="actionError" tone="danger">{{ actionError }}</AppAlert>

      <div v-if="review.screens.length" class="flex flex-wrap items-center gap-1.5">
        <span class="text-[13px] text-ink-muted">Reaches</span>
        <span
          v-for="name in review.screens" :key="name"
          class="flex items-center gap-1 rounded-full bg-raised px-2.5 py-0.5 text-[12px] text-ink"
        >
          <IconTv class="size-3.5 text-ink-muted" aria-hidden="true" />{{ name }}
        </span>
      </div>

      <!-- A playlist change: the same list and preview as the playlist page, read-only, with the
           saved playlist one click away. -->
      <template v-if="review.kind === 'playlist_items'">
        <div class="flex items-center gap-2">
          <button
            v-for="s in (['proposed', 'current'] as const)" :key="s" type="button"
            class="rounded-full px-3 py-1 text-[13px] transition-colors duration-150"
            :class="side === s ? 'bg-ink text-ink-inverse' : 'bg-surface text-ink-muted hover:text-ink'"
            :disabled="s === 'current' && !current"
            @click="side = s"
          >
            {{ s === 'proposed' ? `Proposed · ${proposed.length} scene${proposed.length === 1 ? '' : 's'}`
              : current ? `Current · ${current.length} scene${current.length === 1 ? '' : 's'}` : 'Current · playlist gone' }}
          </button>
          <span v-if="currentName" class="text-[13px] text-ink-subtle">in “{{ currentName }}”</span>
        </div>

        <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <ul class="flex flex-col gap-2">
            <li v-if="!shown.length" class="rounded-xl bg-surface p-3 text-[13px] text-ink-muted">No scenes.</li>
            <li
              v-for="row in shown" :key="row.key"
              class="flex cursor-pointer items-center gap-3 rounded-xl bg-surface p-3 transition-colors duration-200"
              :class="[!row.isEnabled && 'opacity-50', preview.current.value?.key === row.key && 'bg-raised ring-2 ring-ink']"
              @click="preview.select(row)"
            >
              <div class="flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-md bg-raised">
                <img v-if="row.elements[0]?.thumbnailUrl" :src="row.elements[0].thumbnailUrl" :alt="sceneLabel(row)" class="size-full object-cover" />
                <IconLanguage v-else-if="row.elements[0]?.kind === 'web'" class="size-5 text-ink-muted" />
              </div>
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm text-ink">{{ sceneLabel(row) }}</p>
                <p class="text-[13px] text-ink-subtle">
                  {{ row.elements.length }} element{{ row.elements.length === 1 ? '' : 's' }}<template v-if="!row.isEnabled"> · disabled</template>
                </p>
              </div>
              <span class="px-2 py-1 text-[13px] tabular-nums text-ink-subtle">
                {{ duration(row.elements[0]?.kind === 'video' ? row.elements[0]?.mediaDuration ?? row.durationSeconds : row.durationSeconds) }}
              </span>
            </li>
          </ul>

          <div class="flex flex-col gap-3 rounded-xl bg-surface p-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div class="flex flex-wrap items-center gap-2">
                <select
                  v-model="presetId" :disabled="isCustom"
                  class="rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px] text-ink focus:border-ink focus:outline-none disabled:opacity-40"
                >
                  <optgroup v-if="deviceOptions.length" label="Your screens">
                    <option v-for="d in deviceOptions" :key="d.id" :value="d.id">{{ d.label }}</option>
                  </optgroup>
                  <optgroup label="Presets">
                    <option v-for="p in SCREEN_PRESETS" :key="p.id" :value="p.id">{{ p.label }}</option>
                  </optgroup>
                </select>
                <label class="flex items-center gap-1.5 text-[13px] text-ink-muted">
                  <input v-model="isCustom" type="checkbox" class="size-3.5 accent-ink" />
                  Custom
                </label>
                <template v-if="isCustom">
                  <input v-model.number="customWidth" type="number" min="1" class="w-20 rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px] focus:border-ink focus:outline-none" />
                  <span class="text-[13px] text-ink-subtle">×</span>
                  <input v-model.number="customHeight" type="number" min="1" class="w-20 rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px] focus:border-ink focus:outline-none" />
                </template>
              </div>
              <AppButton variant="secondary" size="sm" :disabled="!shown.length" @click="preview.toggle()">
                <component :is="preview.isPlaying.value ? IconPause : IconPlayArrow" class="size-4" aria-hidden="true" />
                {{ preview.isPlaying.value ? 'Pause' : 'Play' }}
              </AppButton>
            </div>
            <ScreenPreview
              :screen-width="screen.width"
              :screen-height="screen.height"
              :elements="preview.current.value?.elements ?? []"
              :background="preview.current.value?.background ?? 'black'"
            />
          </div>
        </div>
      </template>

      <!-- A campaign: its rules, readable. -->
      <div v-else-if="review.kind === 'campaign_create' || review.kind === 'campaign_update'" class="flex flex-col gap-2">
        <p class="text-sm text-ink-muted">Rules, in priority order</p>
        <div v-for="(r, i) in rules" :key="i" class="rounded-xl bg-surface p-3">
          <p class="text-sm text-ink">{{ playlistName(r.playlist_id) }}<span v-if="r.name" class="text-ink-muted"> · {{ r.name }}</span></p>
          <p class="mt-0.5 text-[13px] text-ink-muted">
            {{ daysLabel(r.days_of_week) }} · {{ hhmm(r.starts_at) }}–{{ hhmm(r.ends_at) }}<template v-if="r.priority"> · priority {{ r.priority }}</template>
            <template v-if="r.start_date || r.end_date"> · {{ r.start_date ?? '…' }} to {{ r.end_date ?? '…' }}</template>
          </p>
        </div>
        <p v-if="!rules.length" class="text-[13px] text-ink-muted">No rules.</p>
      </div>

      <div v-else-if="review.kind === 'campaign_delete'" class="rounded-xl bg-surface p-3 text-sm text-ink">
        Removes campaign “{{ review.target_name }}” from every screen it is on. Those screens fall back to whatever else is scheduled, or their default playlist.
      </div>

      <div v-else-if="review.kind === 'playlist_shuffle'" class="rounded-xl bg-surface p-3 text-sm text-ink">
        Shuffle {{ review.payload.shuffle ? 'on' : 'off' }} for “{{ review.target_name }}”. The scenes stay the same; only their order on screen changes.
      </div>

      <div v-else-if="review.kind === 'device_playlist'" class="rounded-xl bg-surface p-3 text-sm text-ink">
        Screen “{{ review.target_name }}” will {{ devicePayload.clear_playlist || !devicePayload.playlist_id ? 'play nothing by default' : `play “${playlistName(devicePayload.playlist_id)}” by default` }}.
      </div>

      <div v-else class="rounded-xl bg-surface p-3 text-sm text-ink">
        {{ review.summary }}
        <template v-if="review.payload.playlist_id"> · {{ playlistName(String(review.payload.playlist_id)) }}</template>
        <template v-if="review.payload.starts_at"> · {{ daysLabel(review.payload.days_of_week as number | undefined) }} {{ hhmm(String(review.payload.starts_at)) }}–{{ hhmm(String(review.payload.ends_at ?? '')) }}</template>
      </div>
    </template>

    <AppModal v-if="rejecting && review" title="Reject this change?" @close="rejecting = false">
      <p class="text-sm text-ink-muted">{{ review.summary }}</p>
      <label class="mt-3 block text-[13px] text-ink-muted">
        Tell {{ review.requested_by_name }} why (optional)
        <textarea
          v-model="rejectNote" rows="3" maxlength="500"
          class="mt-1 w-full rounded-lg border border-line-strong bg-canvas px-2.5 py-1.5 text-sm text-ink focus:border-ink focus:outline-none"
        />
      </label>
      <ModalActions>
        <AppButton variant="secondary" size="sm" @click="rejecting = false">Cancel</AppButton>
        <AppButton variant="danger" size="sm" :loading="isActing" @click="confirmReject">Reject</AppButton>
      </ModalActions>
    </AppModal>
  </div>
</template>
