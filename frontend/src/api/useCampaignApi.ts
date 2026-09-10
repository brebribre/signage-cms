import { request } from '@/api/request'
import type { CampaignRead, CampaignSaveResult, CampaignSummary, CampaignWrite } from '@/types/api'

export function useCampaignApi() {
  return {
    list: () => request<CampaignSummary[]>('GET', '/campaigns'),
    get: (id: string) => request<CampaignRead>('GET', `/campaigns/${id}`),
    create: (body: CampaignWrite) => request<CampaignSaveResult>('POST', '/campaigns', body),
    /** Full replace — a campaign's device list and rules are saved as one set, not patched
     *  field by field. */
    update: (id: string, body: CampaignWrite) =>
      request<CampaignSaveResult>('PUT', `/campaigns/${id}`, body),
    remove: (id: string) => request<void>('DELETE', `/campaigns/${id}`),
  }
}
