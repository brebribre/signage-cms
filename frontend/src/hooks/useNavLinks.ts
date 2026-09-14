import type { Component } from 'vue'
import IconCampaign from '~icons/material-symbols/campaign-outline'
import IconMonitoring from '~icons/material-symbols/monitoring'
import IconPhotoLibrary from '~icons/material-symbols/photo-library-outline'
import IconPlaylistPlay from '~icons/material-symbols/playlist-play'
import IconTv from '~icons/material-symbols/tv-outline'

export interface NavLink {
  name: string
  label: string
  icon: Component
}

export interface NavSection {
  /** null for the ungrouped links at the very top. */
  title: string | null
  links: NavLink[]
}

/** The app's primary page links — shared between the desktop sidebar (which shows the section
 *  titles) and the mobile bottom bar (which flattens them) so the two can never drift apart.
 *  Owner-only pages (Users, Player updates) and the external Documentation link stay in
 *  SidebarContainer.vue alone: there's no room for them in a phone-width bottom bar, and they're
 *  secondary to day-to-day use anyway. */
export function useNavLinks() {
  const sections: NavSection[] = [
    { title: null, links: [{ name: 'now', label: 'Now', icon: IconMonitoring }] },
    {
      title: 'Content',
      links: [
        { name: 'media', label: 'Media', icon: IconPhotoLibrary },
        { name: 'playlists', label: 'Playlists', icon: IconPlaylistPlay },
      ],
    },
    {
      title: 'Deploy',
      links: [
        { name: 'campaigns', label: 'Campaigns', icon: IconCampaign },
        { name: 'devices', label: 'Devices', icon: IconTv },
      ],
    },
  ]

  const primary = sections.flatMap((s) => s.links)

  return { sections, primary }
}
