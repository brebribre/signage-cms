import { request } from '@/api/request'
import type {
  CompleteBody,
  MediaDetail,
  MediaKind,
  MediaRead,
  UploadTicket,
} from '@/types/api'

/** Transport only. The PUT to R2 is not here — it does not go through `request()`,
 *  because it goes to storage rather than to our API, and it needs upload progress. */
export function useMediaApi() {
  return {
    list: (kind?: MediaKind) =>
      request<MediaRead[]>('GET', kind ? `/media?kind=${kind}` : '/media'),
    get: (id: string) => request<MediaDetail>('GET', `/media/${id}`),
    startUpload: (body: { filename: string; content_type: string; size_bytes: number }) =>
      request<UploadTicket>('POST', '/media/uploads', body),
    complete: (id: string, body: CompleteBody) =>
      request<MediaRead>('POST', `/media/${id}/complete`, body),
    remove: (id: string) => request<void>('DELETE', `/media/${id}`),
  }
}
