<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Ref } from 'vue'
import { useRouter } from 'vue-router'
import IconErrorOutline from '~icons/material-symbols/error-outline'
import IconPlaylistPlay from '~icons/material-symbols/playlist-play'
import IconTv from '~icons/material-symbols/tv-outline'

import { useAccountLimits } from '@/hooks/useAccountLimits'
import { useCampaigns } from '@/hooks/useCampaigns'
import { useDevices } from '@/hooks/useDevices'
import { useFleetHealth } from '@/hooks/useFleetHealth'
import { useFormat } from '@/hooks/useFormat'
import { useFleetErrors } from '@/hooks/useFleetErrors'
import { useMedia } from '@/hooks/useMedia'
import { usePlaylists } from '@/hooks/usePlaylists'
import { useReviewBadge, useReviews } from '@/hooks/useReviews'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import AppModal from '@/reusables/AppModal.vue'
import AppTabs from '@/reusables/AppTabs.vue'
import CampaignCard from '@/reusables/CampaignCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import ListRowSkeleton from '@/reusables/ListRowSkeleton.vue'
import OnboardingCard from '@/reusables/OnboardingCard.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import PairScreenForm from '@/reusables/PairScreenForm.vue'
import ReviewCard from '@/reusables/ReviewCard.vue'
import StatCard from '@/reusables/StatCard.vue'
import SkeletonList from '@/reusables/SkeletonList.vue'
import type { ClaimBody, DeviceOrientation } from '@/types/api'

/**
 * Overview: the fleet at a glance — summary figures, then three tabs for the three questions a
 * morning starts with: what is playing (every campaign, and whether it is actually on its
 * screens right now), what is waiting for a decision (reviews), and what went wrong (the newest
 * errors, each with the screen it came from). The screens themselves live on the Screens page.
 */
const router = useRouter()
const {
  items: devices, resolved, isLoading: devicesLoading, error: devicesError,
  isSaving: claiming, claimError, connecting, claim, setOrientation,
} = useDevices()
const { devices: health, storage, offline, withErrors, isLoading: healthLoading } = useFleetHealth()
/** Everything the health endpoint doesn't count as offline — the hero card's line of context. */
const online = computed(() => health.value.filter((d) => d.is_online))
const { items: playlists, isLoading: playlistsLoading, error: playlistsError } = usePlaylists()
/** The account's screen limit, so the Screens figure reads "3 of 5" rather than a bare count. */
const { limits } = useAccountLimits()
const { items: campaigns, isLoading: campaignsLoading } = useCampaigns()
/** Distinct screens covered by any campaign — a screen in two campaigns counts once. */
const campaignScreens = computed(() => new Set(campaigns.value.flatMap((c) => c.device_ids)).size)
const { items: media, isLoading: mediaLoading, error: mediaError } = useMedia()

// --- First steps: a big prompt for whatever the account doesn't have yet ---

/** True once a list has finished its first load without failing — so a prompt never flashes
 *  before the data arrives, and a failed load isn't mistaken for "you have none". */
function loadedOk(loading: Ref<boolean>, error: Ref<string | null>) {
  const ok = ref(false)
  watch(loading, (now, before) => {
    if (before && !now) ok.value = !error.value
  })
  return ok
}
const devicesReady = loadedOk(devicesLoading, devicesError)
const mediaReady = loadedOk(mediaLoading, mediaError)
const playlistsReady = loadedOk(playlistsLoading, playlistsError)

const needsScreen = computed(() => devicesReady.value && !devices.value.length)
const needsMedia = computed(() => mediaReady.value && !media.value.length)
const needsPlaylist = computed(() => playlistsReady.value && !playlists.value.length)

const pairing = ref(false)
async function onClaim(body: ClaimBody) {
  // Once connected the form asks how the screen is mounted; onPairDone finishes from there.
  await claim(body)
}

async function onPairDone(orientation: DeviceOrientation | null) {
  const id = connecting.value?.id
  if (id && orientation && !(await setOrientation(id, orientation))) return
  pairing.value = false
  if (id) router.push({ name: 'device-detail', params: { id } })
}
const { bytes } = useFormat()

// --- Tabs ---

type Tab = 'playing' | 'reviews' | 'errors'
const tab = ref<Tab>('playing')

/** How many of each campaign's screens it is winning on right now, from the per-screen
 *  resolution the manifest itself uses — so "playing on 3 of 5" is what the walls show. */
const playingOn = computed(() => {
  const counts = new Map<string, number>()
  for (const r of resolved.value.values()) {
    if (r.campaign_id) counts.set(r.campaign_id, (counts.get(r.campaign_id) ?? 0) + 1)
  }
  return counts
})

const { pending: pendingReviews, isLoading: reviewsLoading, error: reviewsError, refresh: refreshReviews } = useReviews()
const { pendingCount } = useReviewBadge()
refreshReviews()
const { items: errors, isLoading: errorsLoading, error: errorsError } = useFleetErrors()
const { relativeTime } = useFormat()

const tabs = computed(() => [
  { value: 'playing', label: 'Now playing', badge: campaigns.value.length || undefined },
  { value: 'reviews', label: 'Pending review', badge: pendingCount.value || undefined },
  { value: 'errors', label: 'Errors', badge: errors.value.length || undefined },
])

function quotaPercent(used: number, quota: number | null): number | null {
  return quota ? Math.min(100, Math.round((used / quota) * 100)) : null
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle title="Overview" subtitle="What every screen is playing, right now, and why." />

    <AppAlert v-if="devicesError" tone="danger">{{ devicesError }}</AppAlert>

    <div v-if="needsScreen || needsMedia || needsPlaylist" class="flex flex-col gap-3">
      <OnboardingCard
        v-if="needsScreen"
        :icon="IconTv"
        title="Connect your first screen"
        description="Power on a screen and type the code it shows."
        action="Connect a screen"
        @action="pairing = true"
      />
      <!-- One card for "nothing to play yet", whether that's no media, no playlist or both:
           the playlist editor uploads files itself, so starting at the Media page is a detour
           that leaves you somewhere you still have to leave again. -->
      <OnboardingCard
        v-if="needsMedia || needsPlaylist"
        :icon="IconPlaylistPlay"
        title="Create your first playlist"
        description="Arrange images and videos into a loop a screen can play — upload them as you go."
        action="New playlist"
        @action="router.push({ name: 'playlists', query: { new: '1' } })"
      />
    </div>

    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <!-- One coloured card per row, and it is the figure the page is about. -->
      <!-- "3 of 5" when the account has a screen limit, so the headroom is visible at a glance. -->
      <StatCard
        label="Screens"
        :value="limits?.max_screens != null ? `${devices.length} of ${limits.max_screens}` : devices.length"
        tone="brand" openable :loading="devicesLoading && !devices.length"
        :hint="devices.length ? `${online.length} online now` : 'None paired yet'"
        @open="router.push({ name: 'devices' })"
      />
      <!-- How many campaigns there are, and how far they reach: distinct screens across all of
           them, since one screen can sit in several. -->
      <StatCard
        label="Campaigns" :value="campaigns.length" openable :loading="campaignsLoading && !campaigns.length"
        :hint="campaigns.length
          ? `Across ${campaignScreens} screen${campaignScreens === 1 ? '' : 's'}`
          : 'None yet'"
        @open="router.push({ name: 'campaigns' })"
      />
      <StatCard
        label="Reporting errors" :value="withErrors.length" :tone="withErrors.length ? 'danger' : 'plain'"
        :loading="healthLoading && !health.length"
        :openable="withErrors.length > 0" hint="In the last 24 hours"
        @open="tab = 'errors'"
      />
      <StatCard
        label="Storage" :value="storage ? bytes(storage.used_bytes) : '—'" openable :loading="healthLoading && !storage"
        :hint="storage?.quota_bytes
          ? `of ${bytes(storage.quota_bytes)} (${quotaPercent(storage.used_bytes, storage.quota_bytes)}%)`
          : 'No quota set'"
        @open="router.push({ name: 'media' })"
      />
    </div>

    <AppTabs :items="tabs" :model-value="tab" @update:model-value="tab = $event as Tab" />

    <!-- Now playing: every campaign, with how many of its screens it is winning on right now. -->
    <template v-if="tab === 'playing'">
      <SkeletonList v-if="campaignsLoading && !campaigns.length" label="Loading campaigns">
        <ListRowSkeleton />
      </SkeletonList>
      <EmptyState
        v-else-if="!campaigns.length"
        title="Nothing is scheduled"
        description="A campaign puts playlists on screens on a schedule. Create one and it shows here with the screens it is playing on."
      >
        <template #actions>
          <AppButton size="sm" @click="router.push({ name: 'deploy' })">New campaign</AppButton>
        </template>
      </EmptyState>
      <div v-else class="flex flex-col gap-2">
        <CampaignCard
          v-for="c in campaigns" :key="c.id" :campaign="c"
          :playing-on="playingOn.get(c.id) ?? 0"
          @open="router.push({ name: 'campaign-detail', params: { id: c.id } })"
        />
      </div>
    </template>

    <!-- Pending review: the same cards as the Reviews page, waiting ones only. -->
    <template v-else-if="tab === 'reviews'">
      <AppAlert v-if="reviewsError" tone="danger">{{ reviewsError }}</AppAlert>
      <SkeletonList v-else-if="reviewsLoading && !pendingReviews.length" label="Loading reviews">
        <ListRowSkeleton />
      </SkeletonList>
      <EmptyState
        v-else-if="!pendingReviews.length"
        title="Nothing waiting"
        description="When a manager saves something that would change a screen, it waits here until it is approved."
      >
        <template #actions>
          <AppButton variant="secondary" size="sm" @click="router.push({ name: 'reviews' })">All reviews</AppButton>
        </template>
      </EmptyState>
      <div v-else class="flex flex-col gap-2">
        <ReviewCard
          v-for="r in pendingReviews" :key="r.id" :review="r"
          @open="router.push({ name: 'review-detail', params: { id: r.id } })"
        />
        <AppButton variant="ghost" size="sm" class="self-start" @click="router.push({ name: 'reviews' })">
          All reviews, including decided ones ›
        </AppButton>
      </div>
    </template>

    <!-- Errors: the newest across every screen, each saying which screen it came from. -->
    <template v-else>
      <AppAlert v-if="errorsError" tone="danger">{{ errorsError }}</AppAlert>
      <SkeletonList v-else-if="errorsLoading && !errors.length" label="Loading errors">
        <ListRowSkeleton />
      </SkeletonList>
      <EmptyState
        v-else-if="!errors.length"
        title="No errors reported"
        description="Screens report a problem the moment they hit one — a file that won't play, a website that won't load. None have."
      />
      <AppCard v-else :padded="false">
        <ul class="divide-y divide-line">
          <li v-for="e in errors" :key="e.id">
            <button
              type="button"
              class="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors duration-150 hover:bg-surface"
              @click="router.push({ name: 'device-detail', params: { id: e.device_id } })"
            >
              <IconErrorOutline class="mt-0.5 size-4 shrink-0 text-danger" aria-hidden="true" />
              <span class="min-w-0 flex-1">
                <span class="flex flex-wrap items-baseline justify-between gap-x-3">
                  <span class="text-sm text-ink">{{ e.device_name }}</span>
                  <span class="text-[12px] text-ink-subtle">{{ relativeTime(e.created_at) }}</span>
                </span>
                <span class="mt-0.5 block text-[13px] text-ink-muted [overflow-wrap:anywhere]">{{ e.message }}</span>
              </span>
            </button>
          </li>
        </ul>
      </AppCard>
    </template>

    <AppModal v-if="pairing" title="Connect a screen" @close="pairing = false">
      <PairScreenForm
        :is-saving="claiming" :claim-error="claimError" :connecting="connecting"
        @submit="onClaim"
        @done="onPairDone" @cancel="pairing = false"
      />
    </AppModal>
  </div>
</template>
