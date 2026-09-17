<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { usePlaylistApi } from '@/api/usePlaylistApi'
import { useDeviceResolution } from '@/hooks/useDeviceResolution'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import type { PlaylistDetail } from '@/types/api'

const props = defineProps<{ deviceId: string }>()
const { resolution, isLoading, error } = useDeviceResolution(props.deviceId)
const playlistApi = usePlaylistApi()
const router = useRouter()

/** Assignment only ever happens in Campaigns — so the way out of "nothing playing" is the
 *  deploy flow, with this screen already ticked. The same door for a screen whose playlist
 *  came from somewhere other than a campaign (a default set before campaigns existed). */
function assignInCampaigns() {
  router.push({ name: 'deploy', query: { screen: props.deviceId } })
}
function openPlaylist() {
  const id = resolution.value?.playlist_id
  if (id) router.push({ name: 'playlist-detail', params: { id } })
}
function openCampaign() {
  const id = resolution.value?.campaign_id
  if (id) router.push({ name: 'campaign-detail', params: { id } })
  else assignInCampaigns()
}

const playlist = ref<PlaylistDetail | null>(null)

watch(
  () => resolution.value?.playlist_id,
  async (id) => {
    playlist.value = id ? await playlistApi.get(id).catch(() => null) : null
  },
  { immediate: true },
)

/** One thumbnail per scene — the first element painted in each. Enough to recognize the
 *  loop at a glance without rendering the full layout. */
const thumbnails = computed(() =>
  (playlist.value?.items ?? [])
    .filter((item) => item.is_enabled && item.elements.length)
    .map((item) => {
      const el = item.elements[0]
      // A website has no thumbnail — a blank tile, like any media without one.
      return {
        id: el.id,
        thumbnail_url: el.media?.thumbnail_url ?? null,
        filename: el.media?.filename ?? el.web_url ?? '',
      }
    }),
)
</script>

<template>
  <div class="flex flex-col gap-3">
    <p class="text-sm text-ink-muted">Currently playing</p>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>

    <AppCard v-else-if="resolution?.playlist_id" class="flex flex-col gap-4">
      <div class="flex items-center gap-4">
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm text-ink">{{ playlist?.name ?? '—' }}</p>
          <p v-if="resolution.schedule_name" class="mt-0.5 text-[13px] text-ink-subtle">
            via {{ resolution.schedule_name }}
          </p>
        </div>
        <div
          v-if="thumbnails.length"
          class="flex max-w-[13rem] shrink-0 gap-1.5 overflow-x-auto"
        >
          <div
            v-for="m in thumbnails"
            :key="m.id"
            class="size-14 shrink-0 overflow-hidden rounded-lg bg-raised"
          >
            <img
              v-if="m.thumbnail_url"
              :src="m.thumbnail_url"
              :alt="m.filename"
              class="size-full object-cover"
              loading="lazy"
            />
          </div>
        </div>
      </div>
      <!-- Edit the loop itself, or the rule that put it here. A playlist that arrived without a
           campaign (a default from before campaigns) can only be changed by making one. -->
      <div class="flex flex-wrap gap-2">
        <AppButton size="sm" variant="secondary" @click="openPlaylist">Open playlist</AppButton>
        <AppButton size="sm" variant="secondary" @click="openCampaign">
          {{ resolution.campaign_id ? 'Open campaign' : 'Assign in Campaigns' }}
        </AppButton>
      </div>
    </AppCard>

    <AppCard v-else class="flex flex-wrap items-center justify-between gap-3">
      <p class="text-sm text-ink-muted">No playlist assigned</p>
      <AppButton size="sm" @click="assignInCampaigns">Assign a playlist</AppButton>
    </AppCard>
  </div>
</template>
