<script setup lang="ts">
/**
 * The desktop sidebar: brand, navigation, and whose account you are in.
 *
 * Conventions it follows deliberately, since each one is a thing that is easy to get wrong:
 *
 * - **The current page is never colour alone.** It is weight, a tinted row *and* a bar down its
 *   left edge — legible to someone who can't separate blue from black, and the bar is what makes
 *   it scannable at a glance rather than read.
 * - **Rows are 36px tall with full-width hit areas**, so the target is the row, not the words.
 * - **Real landmarks and names**: one `<nav>`, each group a `<ul>` labelled by its own heading, so
 *   a screen reader announces "Resources, list, 2 items" instead of a wall of links.
 * - **Focus is visible** on every row, because this is the first thing Tab reaches on the page.
 * - **Settings is one link** to a page whose sections are tabs, so the sidebar stays a flat list.
 * - **The account block sits at the bottom**, where every dashboard puts it, and says who you are
 *   and which account before offering the way out.
 *
 * It folds down to its icons (useSidebarCollapsed, remembered per browser) for anyone who wants
 * the width for the page: the logo becomes the mark, headings become hairlines, and every icon
 * keeps its page's name as a tooltip and for screen readers. Nothing is taken away, only words.
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import IconCollapse from '~icons/material-symbols/left-panel-close-outline'
import IconExpand from '~icons/material-symbols/left-panel-open-outline'
import IconLogout from '~icons/material-symbols/logout'
import IconMenuBook from '~icons/material-symbols/menu-book-outline'
import IconOpenInNew from '~icons/material-symbols/open-in-new'

import markUrl from '@/assets/marien-mark.png'
import { useAuth } from '@/hooks/useAuth'
import { useNavLinks } from '@/hooks/useNavLinks'
import { useReviewBadge } from '@/hooks/useReviews'
import { useSidebarCollapsed } from '@/hooks/useSidebarCollapsed'
import AppLogo from '@/reusables/AppLogo.vue'

const router = useRouter()
const { user, account, isOwner, logout } = useAuth()
// Settings is owner-only: one link, whose sections are tabs on its own page.
const { sections, settings } = useNavLinks()
const { collapsed, toggle } = useSidebarCollapsed()

/** Their initials, for the account block — two letters at most, and never an empty circle. */
const initials = computed(() =>
  (user.value?.display_name ?? '?')
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('') || '?',
)

async function onLogout() {
  await logout()
  router.push({ name: 'login' })
}

const FOCUS = 'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-bright'

/** A row: full width with its label, or a centred icon when folded. */
const row = computed(() =>
  'flex w-full items-center rounded-lg py-2 text-sm text-ink transition-colors duration-150 hover:bg-surface ' +
  FOCUS + (collapsed.value ? ' justify-center px-0' : ' gap-3 px-3'),
)

/** The current page. `before:` draws the bar down the row's left edge — the cue that survives
 *  when colour doesn't. Applied through the router-link, so its icon turns blue with it. */
const ROW_ACTIVE =
  'relative bg-brand-soft hover:!bg-brand-soft !text-brand font-medium [&_svg]:!text-brand ' +
  'before:absolute before:left-0 before:top-1.5 before:bottom-1.5 before:w-[3px] ' +
  'before:rounded-full before:bg-brand'

const ICON_BUTTON =
  'shrink-0 rounded-lg p-1.5 text-ink-muted transition-colors duration-150 hover:bg-raised hover:text-ink ' + FOCUS

const { pendingCount, ensureCount } = useReviewBadge()
ensureCount()
</script>

<template>
  <nav
    class="flex flex-col border-r border-line bg-canvas transition-[width] duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]
           motion-reduce:transition-none"
    :class="collapsed ? 'w-[68px]' : 'w-60'"
    aria-label="Main"
  >
    <!-- Brand, and the fold: beside the wordmark when open, under the mark when folded. -->
    <div class="flex items-center pt-6 pb-5" :class="collapsed ? 'flex-col gap-3 px-2' : 'justify-between gap-2 px-5'">
      <img v-if="collapsed" :src="markUrl" alt="Marien" draggable="false" class="size-8 select-none" />
      <AppLogo v-else />
      <button
        type="button"
        :class="ICON_BUTTON"
        :title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        :aria-label="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        :aria-expanded="!collapsed"
        @click="toggle"
      >
        <component :is="collapsed ? IconExpand : IconCollapse" class="size-5" aria-hidden="true" />
      </button>
    </div>

    <div class="flex-1 overflow-x-hidden overflow-y-auto pb-3" :class="collapsed ? 'px-2.5' : 'px-3'">
      <template v-for="(section, index) in [...sections, ...(isOwner ? [settings] : [])]" :key="section.title ?? 'top'">
        <template v-if="section.title">
          <!-- Folded, a heading becomes a hairline: the grouping stays visible without the words. -->
          <p v-if="collapsed" :id="`nav-${index}`" class="sr-only">{{ section.title }}</p>
          <div v-if="collapsed" class="mx-auto my-3 h-px w-6 bg-line" aria-hidden="true" />
          <p
            v-else
            :id="`nav-${index}`"
            class="px-3 pt-5 pb-1.5 text-[11px] font-medium tracking-wider whitespace-nowrap text-ink-subtle uppercase"
          >
            {{ section.title }}
          </p>
        </template>
        <ul class="flex flex-col gap-0.5" :aria-labelledby="section.title ? `nav-${index}` : undefined">
          <li v-for="link in section.links" :key="link.name">
            <!-- Settings links to its parent route, so the row stays current on every Settings tab. -->
            <router-link
              :to="{ name: link.name }"
              :class="row"
              :active-class="ROW_ACTIVE"
              :title="collapsed ? link.label : undefined"
            >
              <span class="relative flex shrink-0">
                <component :is="link.icon" class="size-[18px] text-ink-muted" aria-hidden="true" />
                <!-- Folded, the waiting-review count rides on the icon. -->
                <span
                  v-if="collapsed && link.name === 'reviews' && pendingCount > 0"
                  class="absolute -top-1.5 -right-2 min-w-4 rounded-full bg-brand px-1 text-center text-[10px] leading-4
                         text-ink-inverse tabular-nums"
                  aria-hidden="true"
                >{{ pendingCount }}</span>
              </span>
              <span :class="collapsed ? 'sr-only' : 'truncate'">{{ link.label }}</span>
              <span
                v-if="!collapsed && link.name === 'reviews' && pendingCount > 0"
                class="ml-auto rounded-full bg-brand px-1.5 py-0.5 text-[11px] leading-none text-ink-inverse tabular-nums"
                :aria-label="`${pendingCount} waiting`"
              >{{ pendingCount }}</span>
              <span v-else-if="collapsed && link.name === 'reviews' && pendingCount > 0" class="sr-only">
                , {{ pendingCount }} waiting
              </span>
            </router-link>
          </li>
        </ul>
      </template>
    </div>

    <div class="border-t border-line" :class="collapsed ? 'p-2.5' : 'p-3'">
      <a
        href="https://docs.marien.co.id/"
        target="_blank"
        rel="noopener noreferrer"
        :class="row"
        :title="collapsed ? 'Documentation' : undefined"
      >
        <IconMenuBook class="size-[18px] shrink-0 text-ink-muted" aria-hidden="true" />
        <span :class="collapsed ? 'sr-only' : 'flex-1'">Documentation</span>
        <IconOpenInNew v-if="!collapsed" class="size-3.5 shrink-0 text-ink-subtle" aria-hidden="true" />
        <span class="sr-only">(opens in a new tab)</span>
      </a>

      <!-- Who you are, and the way out. A tinted block rather than loose text: it is a different
           kind of thing from the navigation above it, and shouldn't read as another row. Folded,
           the initials and the way out stack. -->
      <div
        class="mt-2 flex items-center rounded-xl bg-surface p-2.5"
        :class="collapsed ? 'flex-col gap-2 px-0' : 'gap-2.5'"
      >
        <span
          class="flex size-8 shrink-0 items-center justify-center rounded-full bg-brand text-[12px] font-medium text-ink-inverse"
          :title="collapsed ? `${user?.display_name ?? ''} · ${account?.name ?? ''}` : undefined"
          aria-hidden="true"
        >
          {{ initials }}
        </span>
        <div v-if="!collapsed" class="min-w-0 flex-1">
          <p class="truncate text-sm text-ink" :title="user?.display_name">{{ user?.display_name }}</p>
          <p class="truncate text-[12px] text-ink-muted" :title="account?.name">{{ account?.name }}</p>
        </div>
        <button type="button" :class="ICON_BUTTON" title="Sign out" aria-label="Sign out" @click="onLogout">
          <IconLogout class="size-[18px]" aria-hidden="true" />
        </button>
      </div>
    </div>
  </nav>
</template>
