<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { usePlaylistApi } from '@/api/usePlaylistApi'
import { useDeviceResolution } from '@/hooks/useDeviceResolution'
import AppAlert from '@/reusables/AppAlert.vue'
import AppCard from '@/reusables/AppCard.vue'
import type { PlaylistDetail } from '@/types/api'

const props = defineProps<{ deviceId: string }>()
const { resolution, isLoading, error } = useDeviceResolution(props.deviceId)
const playlistApi = usePlaylistApi()

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
    .map((item) => item.elements[0].media),
)
</script>

<template>
  <div class="flex flex-col gap-3">
    <p class="text-sm text-ink-muted">Currently playing</p>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>

    <AppCard v-else-if="resolution?.playlist_id">
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
    </AppCard>

    <AppCard v-else>
      <p class="text-sm text-ink-muted">No playlist assigned</p>
    </AppCard>
  </div>
</template>
