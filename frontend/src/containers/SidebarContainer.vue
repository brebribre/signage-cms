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
 */
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import IconLogout from '~icons/material-symbols/logout'
import IconMenuBook from '~icons/material-symbols/menu-book-outline'
import IconOpenInNew from '~icons/material-symbols/open-in-new'

import { useAuth } from '@/hooks/useAuth'
import { useNavLinks } from '@/hooks/useNavLinks'
import AppLogo from '@/reusables/AppLogo.vue'

const router = useRouter()
const { user, account, isOwner, logout } = useAuth()
// Settings is owner-only: one link, whose sections are tabs on its own page.
const { sections, settings } = useNavLinks()

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

const ROW =
  'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-ink transition-colors ' +
  'duration-150 hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 ' +
  'focus-visible:outline-brand-bright'

/** The current page. `before:` draws the bar down the row's left edge — the cue that survives
 *  when colour doesn't. Applied through the router-link, so its icon turns blue with it. */
const ROW_ACTIVE =
  'relative bg-brand-soft hover:!bg-brand-soft !text-brand font-medium [&_svg]:!text-brand ' +
  'before:absolute before:left-0 before:top-1.5 before:bottom-1.5 before:w-[3px] ' +
  'before:rounded-full before:bg-brand'
</script>

<template>
  <nav class="flex flex-col border-r border-line bg-canvas" aria-label="Main">
    <div class="px-5 pt-6 pb-5">
      <AppLogo />
    </div>

    <div class="flex-1 overflow-y-auto px-3 pb-3">
      <template v-for="(section, index) in sections" :key="section.title ?? 'top'">
        <p
          v-if="section.title"
          :id="`nav-${index}`"
          class="px-3 pt-5 pb-1.5 text-[11px] font-medium tracking-wider text-ink-subtle uppercase"
        >
          {{ section.title }}
        </p>
        <ul class="flex flex-col gap-0.5" :aria-labelledby="section.title ? `nav-${index}` : undefined">
          <li v-for="link in section.links" :key="link.name">
            <router-link :to="{ name: link.name }" :class="ROW" :active-class="ROW_ACTIVE">
              <component :is="link.icon" class="size-[18px] shrink-0 text-ink-muted" aria-hidden="true" />
              {{ link.label }}
            </router-link>
          </li>
        </ul>
      </template>

      <template v-if="isOwner">
        <p id="nav-account" class="px-3 pt-5 pb-1.5 text-[11px] font-medium tracking-wider text-ink-subtle uppercase">
          Account
        </p>
        <ul class="flex flex-col gap-0.5" aria-labelledby="nav-account">
          <li v-for="link in settings.links" :key="link.name">
            <!-- The parent route, so the row stays current on every Settings tab. -->
            <router-link :to="{ name: link.name }" :class="ROW" :active-class="ROW_ACTIVE">
              <component :is="link.icon" class="size-[18px] shrink-0 text-ink-muted" aria-hidden="true" />
              {{ link.label }}
            </router-link>
          </li>
        </ul>
      </template>
    </div>

    <div class="border-t border-line p-3">
      <a
        href="https://docs-production-9a3e.up.railway.app"
        target="_blank"
        rel="noopener noreferrer"
        :class="ROW"
      >
        <IconMenuBook class="size-[18px] shrink-0 text-ink-muted" aria-hidden="true" />
        <span class="flex-1">Documentation</span>
        <IconOpenInNew class="size-3.5 shrink-0 text-ink-subtle" aria-hidden="true" />
        <span class="sr-only">(opens in a new tab)</span>
      </a>

      <!-- Who you are, and the way out. A tinted block rather than loose text: it is a different
           kind of thing from the navigation above it, and shouldn't read as another row. -->
      <div class="mt-2 flex items-center gap-2.5 rounded-xl bg-surface p-2.5">
        <span
          class="flex size-8 shrink-0 items-center justify-center rounded-full bg-brand text-[12px] font-medium text-ink-inverse"
          aria-hidden="true"
        >
          {{ initials }}
        </span>
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm text-ink" :title="user?.display_name">{{ user?.display_name }}</p>
          <p class="truncate text-[12px] text-ink-muted" :title="account?.name">{{ account?.name }}</p>
        </div>
        <button
          type="button"
          class="shrink-0 rounded-lg p-1.5 text-ink-muted transition-colors duration-150 hover:bg-raised
                 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2
                 focus-visible:outline-brand-bright"
          title="Sign out"
          aria-label="Sign out"
          @click="onLogout"
        >
          <IconLogout class="size-[18px]" aria-hidden="true" />
        </button>
      </div>
    </div>
  </nav>
</template>
