import { request } from '@/api/request'
import type { ResolutionRead } from '@/types/api'

export function useScheduleApi() {
  return {
    /** What the screen is playing at this moment, resolved server-side exactly as the
     *  manifest does it. Assigning what plays happens only in Campaigns — this is the only
     *  schedule-related call the frontend still makes. */
    now: (deviceId: string) =>
      request<ResolutionRead>('GET', `/devices/${deviceId}/schedules/now`),
  }
}
