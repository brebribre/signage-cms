import { request } from '@/api/request'
import type { ReviewRead } from '@/types/api'

export function useReviewApi() {
  return {
    list: () => request<ReviewRead[]>('GET', '/reviews'),
    get: (id: string) => request<ReviewRead>('GET', `/reviews/${id}`),
    pendingCount: () => request<{ count: number }>('GET', '/reviews/pending-count'),
    approve: (id: string, note?: string) =>
      request<ReviewRead>('POST', `/reviews/${id}/approve`, { note: note ?? null }),
    reject: (id: string, note?: string) =>
      request<ReviewRead>('POST', `/reviews/${id}/reject`, { note: note ?? null }),
    withdraw: (id: string) => request<ReviewRead>('POST', `/reviews/${id}/withdraw`, {}),
  }
}
