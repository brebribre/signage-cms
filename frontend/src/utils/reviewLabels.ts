import type { Component } from 'vue'
import IconCalendar from '~icons/material-symbols/calendar-month-outline'
import IconCampaign from '~icons/material-symbols/campaign-outline'
import IconPlaylistPlay from '~icons/material-symbols/playlist-play'
import IconShuffle from '~icons/material-symbols/shuffle'
import IconTv from '~icons/material-symbols/tv-outline'

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

/** What a review is about, as an icon — the first thing the list shows on each line. */
export const REVIEW_KIND_ICON: Record<ReviewKind, Component> = {
  playlist_items: IconPlaylistPlay,
  playlist_shuffle: IconShuffle,
  campaign_create: IconCampaign,
  campaign_update: IconCampaign,
  campaign_delete: IconCampaign,
  schedule_create: IconCalendar,
  schedule_update: IconCalendar,
  schedule_delete: IconCalendar,
  device_playlist: IconTv,
}

/** Removals take something off screens, so their icon sits on a quieter, warning-toned tile. */
export const REVIEW_KIND_REMOVES = new Set<ReviewKind>(['campaign_delete', 'schedule_delete'])
