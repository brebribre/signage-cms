import { request } from '@/api/request'
import type { CampaignRead, CampaignSaveResult, CampaignSummary, CampaignWrite, PendingReview } from '@/types/api'

export function useCampaignApi() {
  return {
    list: () => request<CampaignSummary[]>('GET', '/campaigns'),
    get: (id: string) => request<CampaignRead>('GET', `/campaigns/${id}`),
    /** A campaign always reaches screens, so for a manager every one of these answers with a
     *  PendingReview (202) instead of the result — see types/api.ts. */
    create: (body: CampaignWrite) => request<CampaignSaveResult | PendingReview>('POST', '/campaigns', body),
    /** Full replace — a campaign's device list and rules are saved as one set, not patched
     *  field by field. */
    update: (id: string, body: CampaignWrite) =>
      request<CampaignSaveResult | PendingReview>('PUT', `/campaigns/${id}`, body),
    remove: (id: string) => request<void | PendingReview>('DELETE', `/campaigns/${id}`),
  }
}
