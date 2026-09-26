<script setup lang="ts">
import { useReviewBadge } from '@/hooks/useReviews'
/**
 * The sidebar is `hidden` below `lg` (see SidebarView.vue) — this is what replaces it. Same
 * structure as the sidebar, fitted to a phone: an ungrouped link is its own tab, and a category
 * is one tab that opens its pages in a small menu above the bar. Everyone gets a Settings tab, which
 * opens the Settings page (its sections are tabs there) — on a phone, that is also where Log out is. Weight and the brand blue mark the active tab, as in the sidebar.
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useNavLinks } from '@/hooks/useNavLinks'
import type { NavLink, NavSection } from '@/hooks/useNavLinks'

const route = useRoute()
const router = useRouter()
const { sections, settings } = useNavLinks()

type Tab = { kind: 'link'; key: string; link: NavLink } | { kind: 'group'; key: string; section: NavSection }

const tabs = computed<Tab[]>(() => {
  const out: Tab[] = []
  for (const s of sections) {
    if (s.title) out.push({ kind: 'group', key: s.title, section: s })
    else for (const link of s.links) out.push({ kind: 'link', key: link.name, link })
  }
  out.push({ kind: 'link', key: 'settings', link: settings.links[0] })
  return out
})

/** A category tab reads as active on any of its pages — including ones beneath them, like a
 *  single playlist under Playlists. */
function inSection(section: NavSection): boolean {
  return section.links.some((l) => {
    const path = router.resolve({ name: l.name }).path
    return route.path === path || route.path.startsWith(`${path}/`)
  })
}

const openKey = ref<string | null>(null)
const root = ref<HTMLElement | null>(null)

function toggle(key: string) {
  openKey.value = openKey.value === key ? null : key
}

// Closes on navigation, a tap anywhere else, or Escape.
watch(() => route.fullPath, () => { openKey.value = null })
function onDocClick(e: MouseEvent) {
  if (openKey.value && root.value && !root.value.contains(e.target as Node)) openKey.value = null
}
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') openKey.value = null
}
onMounted(() => {
  document.addEventListener('click', onDocClick)
  document.addEventListener('keydown', onKey)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('keydown', onKey)
})

/** Keeps the menu on screen: the first tab's opens rightward, the last tab's leftward. */
function menuPosition(index: number): string {
  if (index === 0) return 'left-2'
  if (index === tabs.value.length - 1) return 'right-2'
  return 'left-1/2 -translate-x-1/2'
}

// Centred and allowed two lines: "Content Management" is wider than a quarter of a phone.
const TAB = 'flex w-full flex-1 flex-col items-center gap-0.5 px-1 py-2 text-center text-[11px] leading-tight transition-colors duration-150'

const { pendingCount, ensureCount } = useReviewBadge()
ensureCount()
</script>

<template>
  <nav
    ref="root"
    class="relative flex items-stretch justify-around border-t border-line bg-canvas"
    style="padding-bottom: env(safe-area-inset-bottom)"
  >
    <template v-for="(tab, index) in tabs" :key="tab.key">
      <router-link
        v-if="tab.kind === 'link'"
        :to="{ name: tab.link.name }"
        :class="[TAB, 'text-ink-muted']"
        active-class="!text-brand font-medium"
      >
        <component :is="tab.link.icon" class="size-5" />
        {{ tab.link.label }}
      </router-link>

      <div v-else class="flex flex-1">
        <button
          type="button"
          :class="[TAB, inSection(tab.section) || openKey === tab.key ? 'font-medium text-brand' : 'text-ink-muted']"
          :aria-expanded="openKey === tab.key"
          aria-haspopup="menu"
          @click="toggle(tab.key)"
        >
          <component :is="tab.section.icon" class="size-5" />
          {{ tab.section.title }}
        </button>

        <div
          v-if="openKey === tab.key"
          class="absolute bottom-full z-30 mb-2 w-52 overflow-hidden rounded-xl border border-line bg-canvas p-1"
          :class="menuPosition(index)"
          role="menu"
        >
          <router-link
            v-for="link in tab.section.links"
            :key="link.name"
            :to="{ name: link.name }"
            class="flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm text-ink-muted transition-colors
                   duration-150 hover:bg-surface hover:text-ink"
            active-class="bg-brand-soft !text-brand font-medium"
            role="menuitem"
          >
            <component :is="link.icon" class="size-[18px] shrink-0" />
            {{ link.label }}
            <span
              v-if="link.name === 'reviews' && pendingCount > 0"
              class="ml-auto rounded-full bg-brand px-1.5 py-0.5 text-[11px] leading-none text-ink-inverse tabular-nums"
            >{{ pendingCount }}</span>
          </router-link>
        </div>
      </div>
    </template>
  </nav>
</template>
