<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import IconTv from '~icons/material-symbols/tv-outline'

import { useDevices } from '@/hooks/useDevices'
import { useFormat } from '@/hooks/useFormat'
import { useNowPlaying } from '@/hooks/useNowPlaying'
import { usePlaylists } from '@/hooks/usePlaylists'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import DeviceCardSkeleton from '@/reusables/DeviceCardSkeleton.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import ScreenShape from '@/reusables/ScreenShape.vue'
import SkeletonList from '@/reusables/SkeletonList.vue'
import StatusDot from '@/reusables/StatusDot.vue'
import ThumbnailStrip from '@/reusables/ThumbnailStrip.vue'
import type { PlaylistSummary } from '@/types/api'

/**
 * Live Control, the list: every screen and what it is playing, one big card each. Open a card to
 * drive that screen by hand. Screens being held on a scene right now are marked, so a demo left
 * running somewhere is never a mystery.
 */
const router = useRouter()
const { items: devices, resolved, isLoading, error, refresh } = useDevices()
const { items: playlists } = usePlaylists()
const { nowPlaying } = useNowPlaying(resolved, playlists)
const { relativeTime } = useFormat()

/** The playlist each screen resolves to — for its thumbnail strip. */
const playlistFor = computed(() => {
  const byId = new Map(playlists.value.map((p) => [p.id, p]))
  return (deviceId: string): PlaylistSummary | null => {
    const id = resolved.value.get(deviceId)?.playlist_id
    return id ? byId.get(id) ?? null : null
  }
})

// A hold started or ended elsewhere (another tab, the timeout) shows up without a reload.
let timer: ReturnType<typeof setInterval> | null = null
onMounted(() => { timer = setInterval(refresh, 10_000) })
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle
      title="Live Control"
      subtitle="Pick a screen, then put any scene of its playlist on it — right now."
    />

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <SkeletonList v-if="isLoading && !devices.length" label="Loading screens" :count="3">
      <DeviceCardSkeleton />
    </SkeletonList>

    <EmptyState
      v-else-if="!devices.length"
      title="No screens yet"
      description="Connect a screen first — then you can drive it from here."
    >
      <template #actions>
        <AppButton size="sm" @click="router.push({ name: 'devices' })">Go to Screens</AppButton>
      </template>
    </EmptyState>

    <div v-else class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <button
        v-for="d in devices"
        :key="d.id"
        type="button"
        class="flex flex-col gap-4 rounded-2xl bg-canvas p-5 text-left transition-colors duration-200 hover:bg-surface
               focus-visible:ring-2 focus-visible:ring-brand focus-visible:outline-none"
        @click="router.push({ name: 'live-device', params: { id: d.id } })"
      >
        <div class="flex items-center gap-4">
          <ScreenShape :device="d" :size="64" />
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <p class="min-w-0 truncate text-lg text-ink">{{ d.name || 'Unnamed screen' }}</p>
              <StatusDot :last-seen-at="d.last_seen_at" :show-label="false" class="shrink-0" />
            </div>
            <p class="mt-0.5 truncate text-[13px] text-ink-muted">
              {{ d.location || relativeTime(d.last_seen_at) }}
            </p>
          </div>
          <!-- Somebody is holding this screen on one scene. -->
          <span
            v-if="d.live_slot_id"
            class="flex shrink-0 items-center gap-1.5 rounded-full bg-brand px-2.5 py-1 text-[11px] font-medium tracking-wider text-ink-inverse uppercase"
          >
            <span class="size-1.5 animate-pulse rounded-full bg-ink-inverse" aria-hidden="true" />
            Live
          </span>
        </div>

        <div class="flex flex-col gap-2">
          <p class="flex items-center gap-2 text-sm text-ink">
            <IconTv class="size-4 shrink-0 text-ink-subtle" aria-hidden="true" />
            <span class="min-w-0 truncate">
              {{ nowPlaying(d.id).text }}<span v-if="nowPlaying(d.id).via" class="text-ink-subtle"> {{ nowPlaying(d.id).via }}</span>
            </span>
          </p>
          <ThumbnailStrip
            v-if="playlistFor(d.id)"
            :thumbnails="playlistFor(d.id)!.thumbnails"
            :total="playlistFor(d.id)!.item_count"
            :tile="72"
          />
          <p v-else class="text-[13px] text-ink-subtle">Nothing to control until a playlist is assigned.</p>
        </div>
      </button>
    </div>
  </div>
</template>
