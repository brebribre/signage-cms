import { request } from '@/api/request'
import type {
  ResolutionRead,
  ScheduleRead,
  ScheduleUpdateBody,
  ScheduleWrite,
} from '@/types/api'

export function useScheduleApi() {
  return {
    list: (deviceId: string) =>
      request<ScheduleRead[]>('GET', `/devices/${deviceId}/schedules`),
    create: (deviceId: string, body: ScheduleWrite) =>
      request<ScheduleRead>('POST', `/devices/${deviceId}/schedules`, body),
    /** What the screen is playing at this moment, resolved server-side exactly as the
     *  manifest does it — so the CMS can show the effect of a rule without waiting for the
     *  window to come round. */
    now: (deviceId: string) =>
      request<ResolutionRead>('GET', `/devices/${deviceId}/schedules/now`),
    update: (id: string, body: ScheduleUpdateBody) =>
      request<ScheduleRead>('PATCH', `/schedules/${id}`, body),
    remove: (id: string) => request<void>('DELETE', `/schedules/${id}`),
  }
}
