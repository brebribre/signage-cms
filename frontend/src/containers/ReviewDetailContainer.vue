<script setup lang="ts">
/**
 * One review, opened: the change shown the way the playlist page shows a playlist — the scene
 * list and the screen preview — with the saved playlist a click away for comparison. A campaign
 * change gets the same treatment (ReviewCampaignContainer): its week, and each rule's playlist
 * on a screen. Read-only:
 * the only things anyone can do here are approve, reject or withdraw. A manager sees exactly
 * this page for their own reviews, minus the owner's buttons.
 */
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import IconArrowBack from '~icons/material-symbols/arrow-back'
import IconCheck from '~icons/material-symbols/check'
import IconClose from '~icons/material-symbols/close'
import IconLanguage from '~icons/material-symbols/language'
import IconText from '~icons/material-symbols/text-fields'
import IconPlaylistPlay from '~icons/material-symbols/playlist-play'
import IconTv from '~icons/material-symbols/tv-outline'

import { useAuth } from '@/hooks/useAuth'
import { useDevices } from '@/hooks/useDevices'
import { useFormat } from '@/hooks/useFormat'
import { useMedia } from '@/hooks/useMedia'
import { usePlaylistPreview } from '@/hooks/usePlaylistPreview'
import { usePlaylists } from '@/hooks/usePlaylists'
import { useReviewDetail } from '@/hooks/useReviewDetail'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppModal from '@/reusables/AppModal.vue'
import AppTabs from '@/reusables/AppTabs.vue'
import ReviewCampaignContainer from '@/containers/ReviewCampaignContainer.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import NamePills from '@/reusables/NamePills.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import ReviewPreviewPanel from '@/reusables/ReviewPreviewPanel.vue'
import SkeletonBlock from '@/reusables/SkeletonBlock.vue'
import type { DraftItem } from '@/hooks/usePlaylistEditor'
import { REVIEW_KIND_LABEL as KIND_LABEL, REVIEW_STATUS as STATUS } from '@/utils/reviewLabels'
import { reviewScreens } from '@/utils/reviewScreens'

const route = useRoute()
const router = useRouter()
const id = route.params.id as string

const { isOwner } = useAuth()
const { relativeTime, duration } = useFormat()
const { items: library } = useMedia()
const { items: devices } = useDevices()
const { items: playlists } = usePlaylists()
const { review, proposed, current, campaignBefore, campaignAfter, rulePlaylists, isLoading, error, isActing, actionError, approve, reject, withdraw } =
  useReviewDetail(id, () => library.value)

/** The screens the change reaches, at the shape they had when it was sent — the only ones the
 *  preview offers. */
const previewScreens = computed(() => (review.value ? reviewScreens(review.value, devices.value) : []))

// --- Playlist changes: Before (the saved playlist) and After (the change), one preview.
// After is what needs judging, so it opens first; Before is one tab away. ---
const side = ref<'proposed' | 'current'>('proposed')
const sideTabs = computed(() => [
  ...(current.value ? [{ value: 'current', label: 'Before', badge: current.value.length }] : []),
  { value: 'proposed', label: 'After', badge: proposed.value.length },
])
const shown = computed<DraftItem[]>(() => (side.value === 'current' ? current.value ?? [] : proposed.value))
const preview = usePlaylistPreview(() => shown.value)
watch(side, () => preview.select(shown.value[0] ?? { key: '' } as DraftItem))

function sceneLabel(item: DraftItem): string {
  if (!item.elements.length) return 'Empty scene'
  const first = item.elements[0].filename
  return item.elements.length > 1 ? `${first} + ${item.elements.length - 1}` : first
}

// --- Schedule changes: the window, readable ---
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
        <span class="text-ink">{{ KIND_LABEL[review.kind] }}</span>
        · sent by {{ review.requested_by_name }} {{ relativeTime(review.created_at) }}<template v-if="review.reviewed_at">
          · decided {{ relativeTime(review.reviewed_at) }}</template>
      </p>
      <AppAlert v-if="review.note">“{{ review.note }}”</AppAlert>
      <AppAlert v-if="actionError" tone="danger">{{ actionError }}</AppAlert>

      <dl class="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-2.5 gap-y-1.5">
        <dt class="flex" title="Screens"><IconTv class="size-4 text-ink-muted" aria-label="Screens" /></dt>
        <dd><NamePills :names="review.screens" noun="screens" :max="8" /></dd>
        <dt class="flex" title="Playlists"><IconPlaylistPlay class="size-4 text-ink-muted" aria-label="Playlists" /></dt>
        <dd><NamePills :names="review.playlists" noun="playlists" :max="8" /></dd>
      </dl>

      <!-- A playlist change: the same list and preview as the playlist page, read-only, with the
           saved playlist one click away. -->
      <template v-if="review.kind === 'playlist_items'">
        <AppTabs :items="sideTabs" :model-value="side" @update:model-value="side = $event as 'proposed' | 'current'" />
        <p v-if="!current" class="-mt-3 text-[13px] text-ink-subtle">The playlist this changes no longer exists, so there is no Before.</p>

        <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <ul class="flex flex-col gap-2">
            <li v-if="!shown.length" class="rounded-xl bg-surface p-3 text-[13px] text-ink-muted">No scenes.</li>
            <li
              v-for="row in shown" :key="row.key"
              class="flex cursor-pointer items-center gap-3 rounded-xl bg-surface p-3 transition-colors duration-200"
              :class="[!row.isEnabled && 'opacity-50', preview.current.value?.key === row.key && 'bg-raised ring-2 ring-ink']"
              @click="preview.select(row)"
            >
              <div
                class="flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-md bg-raised"
                :style="!row.elements[0]?.thumbnailUrl && row.background === 'color' && row.backgroundColor ? { background: row.backgroundColor } : undefined"
              >
                <img v-if="row.elements[0]?.thumbnailUrl" :src="row.elements[0].thumbnailUrl" :alt="sceneLabel(row)" class="size-full object-cover" />
                <IconLanguage v-else-if="row.elements[0]?.kind === 'web'" class="size-5 text-ink-muted" />
                <IconText
                  v-else-if="row.elements[0]?.kind === 'text'"
                  class="size-5"
                  :class="row.background === 'color' && row.backgroundColor ? 'text-white/85' : 'text-ink-muted'"
                />
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

          <ReviewPreviewPanel :preview="preview" :screens="previewScreens" />
        </div>
      </template>

      <!-- A campaign: when it plays, where, and each rule's playlist on a screen — Before and
           After, as a playlist change has. -->
      <ReviewCampaignContainer
        v-else-if="review.kind === 'campaign_create' || review.kind === 'campaign_update' || review.kind === 'campaign_delete'"
        :kind="review.kind"
        :before="campaignBefore"
        :after="campaignAfter"
        :playlists="rulePlaylists"
        :devices="devices"
        :screens="previewScreens"
      />

      <div v-else-if="review.kind === 'playlist_shuffle'" class="rounded-xl bg-surface p-3 text-sm text-ink">
        Shuffle {{ review.payload.shuffle ? 'on' : 'off' }} for “{{ review.target_name }}”<template v-if="review.before"> (it was {{ review.before.shuffle ? 'on' : 'off' }})</template>.
        The scenes stay the same; only their order on screen changes.
      </div>

      <div v-else-if="review.kind === 'device_playlist'" class="rounded-xl bg-surface p-3 text-sm text-ink">
        Screen “{{ review.target_name }}” will {{ devicePayload.clear_playlist || !devicePayload.playlist_id ? 'play nothing by default' : `play “${playlistName(devicePayload.playlist_id)}” by default` }}<template v-if="review.before">,
          instead of {{ review.before.playlist_name ? `“${review.before.playlist_name}”` : 'nothing' }}</template>.
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
