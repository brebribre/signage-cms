/** The app's primary page links — shared between the desktop sidebar and the mobile bottom
 *  bar so the two can never drift apart. Owner-only pages (Users, Player updates) and the
 *  external Documentation link stay in SidebarContainer.vue alone: there's no room for them
 *  in a phone-width bottom bar, and they're secondary to day-to-day use anyway. */
export function useNavLinks() {
  const primary = [
    // Temporary: the redesign's proposed replacement for Devices+Health (UX_REDESIGN_PLAN.md
    // §3), added alongside them rather than in place of them so it can be compared directly
    // in the running app before either old page is removed. Remove Devices and/or Health from
    // this list once that comparison is done — see the plan's §8 phasing.
    { name: 'now', label: 'Now' },
    { name: 'media', label: 'Media' },
    { name: 'playlists', label: 'Playlists' },
    { name: 'campaigns', label: 'Campaigns' },
    { name: 'devices', label: 'Devices' },
    { name: 'health', label: 'Health' },
  ] as const

  return { primary }
}
