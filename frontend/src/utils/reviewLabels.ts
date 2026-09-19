import type { ReviewKind, ReviewStatus } from '@/types/api'

/** What a review is, in plain words — shown on the list card and the review page alike. */
export const REVIEW_KIND_LABEL: Record<ReviewKind, string> = {
  playlist_items: 'Playlist change',
  playlist_shuffle: 'Playlist shuffle',
  campaign_create: 'New campaign',
  campaign_update: 'Campaign change',
  campaign_delete: 'Campaign removal',
  schedule_create: 'New schedule',
  schedule_update: 'Schedule change',
  schedule_delete: 'Schedule removal',
  device_playlist: 'Screen assignment',
}

export const REVIEW_STATUS: Record<ReviewStatus, { label: string; cls: string }> = {
  pending: { label: 'Waiting', cls: 'bg-brand-soft text-brand' },
  approved: { label: 'Approved', cls: 'bg-emerald-50 text-emerald-700' },
  rejected: { label: 'Rejected', cls: 'bg-raised text-danger' },
  withdrawn: { label: 'Withdrawn', cls: 'bg-raised text-ink-muted' },
}
