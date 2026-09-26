import type { Component } from 'vue'
import IconCorporate from '~icons/material-symbols/corporate-fare'
import IconDns from '~icons/material-symbols/dns-outline'

export interface NavLink {
  name: string
  label: string
  icon: Component
}

export interface NavSection {
  title: string
  links: NavLink[]
}

/** The app's pages, in one place for both the desktop sidebar and the phone's top-bar menu, so
 *  the two can never drift apart. Grouped the way the CMS's sidebar is: a heading per kind of
 *  thing, so a new page has an obvious place to go. */
const SECTIONS: NavSection[] = [
  { title: 'Customers', links: [{ name: 'accounts', label: 'Accounts', icon: IconCorporate }] },
  { title: 'Platform', links: [{ name: 'infrastructure', label: 'Infrastructure', icon: IconDns }] },
]

export function useNavLinks() {
  return { sections: SECTIONS }
}
