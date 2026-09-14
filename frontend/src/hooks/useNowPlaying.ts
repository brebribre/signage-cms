import type { Ref } from 'vue'

import type { DeviceResolutionRead, PlaylistSummary } from '@/types/api'

/** The "currently playing" line on every device card — resolved server-side from the screen's
 *  campaigns, named from the playlist list. One place, so the Devices list, the deploy picker
 *  and the rollout picker can never word it differently. Read-only: what a screen plays is
 *  decided in Campaigns. */
export function useNowPlaying(
  resolved: Ref<Map<string, DeviceResolutionRead>>,
  playlists: Ref<PlaylistSummary[]>,
) {
  function nowPlaying(deviceId: string): { text: string; via: string | null } {
    const r = resolved.value.get(deviceId)
    if (!r?.playlist_id) return { text: 'No playlist', via: null }
    return {
      text: playlists.value.find((p) => p.id === r.playlist_id)?.name ?? '—',
      via: r.schedule_name ? `via “${r.schedule_name}”` : null,
    }
  }

  return { nowPlaying }
}
