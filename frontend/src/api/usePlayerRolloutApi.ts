import { request } from '@/api/request'
import type { PlayerReleaseRead, PlayerRolloutRead, PlayerRolloutWrite } from '@/types/api'

export function usePlayerRolloutApi() {
  return {
    releases: () => request<PlayerReleaseRead[]>('GET', '/player-rollouts/releases'),
    rollouts: () => request<PlayerRolloutRead[]>('GET', '/player-rollouts/rollouts'),
    schedule: (body: PlayerRolloutWrite) =>
      request<PlayerRolloutRead>('POST', '/player-rollouts/rollouts', body),
    cancel: (id: string) => request<void>('DELETE', `/player-rollouts/rollouts/${id}`),
  }
}
