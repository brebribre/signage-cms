import { request } from '@/api/request'
import type { ResolutionRead, ScheduleRead } from '@/types/api'

/** Read-only from the frontend — creating or changing a schedule rule happens only through
 *  Campaigns, which writes these rows directly rather than going through this API. */
export function useScheduleApi() {
  return {
    list: (deviceId: string) =>
      request<ScheduleRead[]>('GET', `/devices/${deviceId}/schedules`),
    /** What the screen is playing at this moment, resolved server-side exactly as the
     *  manifest does it. */
    now: (deviceId: string) =>
      request<ResolutionRead>('GET', `/devices/${deviceId}/schedules/now`),
  }
}
