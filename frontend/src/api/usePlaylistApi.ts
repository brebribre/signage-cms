import { request } from '@/api/request'
import type { ItemWrite, PlaylistDetail, PlaylistSummary } from '@/types/api'

export function usePlaylistApi() {
  return {
    list: () => request<PlaylistSummary[]>('GET', '/playlists'),
    get: (id: string) => request<PlaylistDetail>('GET', `/playlists/${id}`),
    create: (name: string) => request<PlaylistDetail>('POST', '/playlists', { name }),
    update: (id: string, body: { name?: string; shuffle?: boolean }) =>
      request<PlaylistDetail>('PATCH', `/playlists/${id}`, body),
    /** Replaces the whole list — there is deliberately no reorder or insert endpoint. */
    replaceItems: (id: string, items: ItemWrite[]) =>
      request<PlaylistDetail>('PUT', `/playlists/${id}/items`, { items }),
    remove: (id: string) => request<void>('DELETE', `/playlists/${id}`),
  }
}
