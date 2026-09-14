import type { Component } from 'vue'
import IconCampaign from '~icons/material-symbols/campaign-outline'
import IconFolderOpen from '~icons/material-symbols/folder-open-outline'
import IconGroup from '~icons/material-symbols/group-outline'
import IconMonitoring from '~icons/material-symbols/monitoring'
import IconPhotoLibrary from '~icons/material-symbols/photo-library-outline'
import IconPlaylistPlay from '~icons/material-symbols/playlist-play'
import IconRocket from '~icons/material-symbols/rocket-launch-outline'
import IconSettings from '~icons/material-symbols/settings-outline'
import IconSystemUpdate from '~icons/material-symbols/system-update-alt'
import IconTv from '~icons/material-symbols/tv-outline'

export interface NavLink {
  name: string
  label: string
  icon: Component
}

export interface NavSection {
  /** null for the ungrouped links at the very top. */
  title: string | null
  /** The category's own icon — its tab on the mobile bar. Null when ungrouped. */
  icon: Component | null
  links: NavLink[]
}

/** The app's page links, in one place for both the desktop sidebar (section titles, a
 *  collapsible Settings row) and the mobile bar (a tab per ungrouped link, a tab per category
 *  that opens its pages above the bar) — so the two can never drift apart. `settings` is
 *  owner-only; callers gate it. The external Documentation link stays in SidebarContainer. */
export function useNavLinks() {
  const sections: NavSection[] = [
    { title: null, icon: null, links: [{ name: 'now', label: 'Overview', icon: IconMonitoring }] },
    {
      title: 'Content',
      icon: IconFolderOpen,
      links: [
        { name: 'media', label: 'Media', icon: IconPhotoLibrary },
        { name: 'playlists', label: 'Playlists', icon: IconPlaylistPlay },
      ],
    },
    {
      title: 'Deploy',
      icon: IconRocket,
      links: [
        { name: 'campaigns', label: 'Campaigns', icon: IconCampaign },
        { name: 'devices', label: 'Devices', icon: IconTv },
      ],
    },
  ]

  const settings: NavSection = {
    title: 'Settings',
    icon: IconSettings,
    links: [
      { name: 'settings-users', label: 'User Management', icon: IconGroup },
      { name: 'settings-updates', label: 'Software updates', icon: IconSystemUpdate },
    ],
  }

  const primary = sections.flatMap((s) => s.links)

  return { sections, settings, primary }
}
