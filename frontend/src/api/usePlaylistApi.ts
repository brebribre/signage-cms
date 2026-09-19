import { request } from '@/api/request'
import type { ItemWrite, PendingReview, PlaylistDetail, PlaylistSummary } from '@/types/api'

export function usePlaylistApi() {
  return {
    list: () => request<PlaylistSummary[]>('GET', '/playlists'),
    get: (id: string) => request<PlaylistDetail>('GET', `/playlists/${id}`),
    create: (name: string) => request<PlaylistDetail>('POST', '/playlists', { name }),
    /** A manager's shuffle change on a playlist that is on screens comes back as a
     *  PendingReview (202) instead — see types/api.ts. A rename never does. */
    update: (id: string, body: { name?: string; shuffle?: boolean }) =>
      request<PlaylistDetail | PendingReview>('PATCH', `/playlists/${id}`, body),
    /** Replaces the whole list — there is deliberately no reorder or insert endpoint. For a
     *  manager, a playlist that is on screens answers with a PendingReview (202). */
    replaceItems: (id: string, items: ItemWrite[]) =>
      request<PlaylistDetail | PendingReview>('PUT', `/playlists/${id}/items`, { items }),
    remove: (id: string) => request<void>('DELETE', `/playlists/${id}`),
  }
}
