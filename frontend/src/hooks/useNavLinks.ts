/** The app's primary page links — shared between the desktop sidebar and the mobile bottom
 *  bar so the two can never drift apart. Owner-only pages (Users, Player updates) and the
 *  external Documentation link stay in SidebarContainer.vue alone: there's no room for them
 *  in a phone-width bottom bar, and they're secondary to day-to-day use anyway. */
export function useNavLinks() {
  const primary = [
    { name: 'media', label: 'Media' },
    { name: 'playlists', label: 'Playlists' },
    { name: 'campaigns', label: 'Campaigns' },
    { name: 'devices', label: 'Devices' },
    { name: 'health', label: 'Health' },
  ] as const

  return { primary }
}
