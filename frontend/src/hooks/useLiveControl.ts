import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

import { ApiError } from '@/api/request'
import { useDeviceApi } from '@/api/useDeviceApi'
import { usePlaylistApi } from '@/api/usePlaylistApi'
import { useScheduleApi } from '@/api/useScheduleApi'
import { toDraftElement } from '@/hooks/usePlaylistEditor'
import type { DraftElement } from '@/hooks/usePlaylistEditor'
import type { DeviceRead, PlaylistDetail, ResolutionRead, SceneBackground } from '@/types/api'

/** One scene of the screen's playlist, ready to draw as a tile and to hold the screen on. */
export interface LiveScene {
  id: string
  /** 1-based, as people count scenes. */
  number: number
  durationSeconds: number
  background: SceneBackground
  backgroundColor: string | null
  elements: DraftElement[]
  /** What to call it: the first element's file name, website, or text. */
  label: string
}

/** Refreshed this often, so a hold that ended elsewhere (another tab, the timeout) or a playlist
 *  change shows up without a reload. Cheap: one device read and one resolve. */
const REFRESH_MS = 5_000

/**
 * Live Control for one screen: what it is playing, the scenes it could be holding, and the
 * two moves — hold a scene, end the hold. The screen itself is pushed by the server, so a hold
 * lands on the wall within a couple of seconds; nothing here waits for that.
 */
export function useLiveControl(deviceId: string) {
  const deviceApi = useDeviceApi()
  const scheduleApi = useScheduleApi()
  const playlistApi = usePlaylistApi()

  const device = ref<DeviceRead | null>(null)
  const resolution = ref<ResolutionRead | null>(null)
  const playlist = ref<PlaylistDetail | null>(null)
  const isLoading = ref(true)
  const error = ref<string | null>(null)
  /** The scene a hold is being sent for, while the request is in flight — the tile shows it. */
  const pendingSlotId = ref<string | null>(null)
  const isEnding = ref(false)
  const actionError = ref<string | null>(null)

  async function refresh() {
    try {
      const [d, r] = await Promise.all([deviceApi.get(deviceId), scheduleApi.now(deviceId)])
      device.value = d
      resolution.value = r
      error.value = null
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : 'Could not load this screen'
    } finally {
      isLoading.value = false
    }
  }

  // The playlist is fetched only when the screen's answer changes — not on every refresh.
  watch(
    () => resolution.value?.playlist_id ?? null,
    async (id) => {
      playlist.value = id ? await playlistApi.get(id).catch(() => null) : null
    },
    { immediate: true },
  )

  let timer: ReturnType<typeof setInterval> | null = null
  onMounted(() => {
    refresh()
    timer = setInterval(refresh, REFRESH_MS)
  })
  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  const scenes = computed<LiveScene[]>(() =>
    (playlist.value?.items ?? [])
      .filter((item) => item.is_enabled && item.elements.length)
      .map((item, i) => {
        const elements = item.elements.map(toDraftElement)
        const first = [...elements].sort((a, b) => a.zIndex - b.zIndex)[0]
        return {
          id: item.id,
          number: i + 1,
          durationSeconds: item.duration_seconds,
          background: item.background,
          backgroundColor: item.background_color ?? null,
          elements,
          label: first.kind === 'text' ? (first.text ?? 'Text') : first.kind === 'web' ? 'Website' : first.filename,
        }
      }),
  )

  const liveSlotId = computed(() => device.value?.live_slot_id ?? null)
  const liveScene = computed(() => scenes.value.find((s) => s.id === liveSlotId.value) ?? null)

  async function hold(slotId: string) {
    pendingSlotId.value = slotId
    actionError.value = null
    try {
      device.value = await deviceApi.setLive(deviceId, { slot_id: slotId })
    } catch (e) {
      actionError.value = e instanceof ApiError ? e.message : 'Could not put that scene on the screen'
      // A 409 means the playlist changed under this page — show what the screen has now.
      await refresh()
    } finally {
      pendingSlotId.value = null
    }
  }

  async function end() {
    isEnding.value = true
    actionError.value = null
    try {
      device.value = await deviceApi.endLive(deviceId)
    } catch (e) {
      actionError.value = e instanceof ApiError ? e.message : 'Could not end live control'
    } finally {
      isEnding.value = false
    }
  }

  return {
    device, resolution, playlist, scenes, liveSlotId, liveScene,
    isLoading, error, actionError, pendingSlotId, isEnding,
    refresh, hold, end,
  }
}
