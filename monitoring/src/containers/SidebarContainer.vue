<script setup lang="ts">
/**
 * The desktop sidebar: brand, the pages, and who is signed in — built the same way as the CMS's
 * (frontend/src/containers/SidebarContainer.vue), so staff moving between the two find things
 * where they left them.
 *
 * - **The current page is never colour alone**: weight, a tinted row *and* a bar down its left
 *   edge.
 * - **Rows are the hit area**, not the words, and every row shows focus.
 * - **One `<nav>`, each group a `<ul>` labelled by its heading**, so a screen reader announces
 *   "Platform, list, 1 item" rather than a run of links.
 * - **Who you are sits at the bottom**, with the way out beside it.
 */
import { useRouter } from 'vue-router'
import IconLogout from '~icons/material-symbols/logout'

import { initials } from '@/hooks/useAccountMarks'
import { useAuth } from '@/hooks/useAuth'
import { useNavLinks } from '@/hooks/useNavLinks'
import { useStaffRights } from '@/hooks/useStaffRights'
import AppLogo from '@/reusables/AppLogo.vue'

const router = useRouter()
const { user, logout } = useAuth()
const { label: kindLabel } = useStaffRights()
const { sections } = useNavLinks()

async function onLogout() {
  await logout()
  router.push({ name: 'login' })
}

const ROW =
  'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-ink transition-colors ' +
  'duration-150 hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 ' +
  'focus-visible:outline-brand-bright'

/** `before:` draws the bar down the row's left edge — the cue that survives when colour doesn't. */
const ROW_ACTIVE =
  'relative bg-brand-soft hover:!bg-brand-soft !text-brand font-medium [&_svg]:!text-brand ' +
  'before:absolute before:left-0 before:top-1.5 before:bottom-1.5 before:w-[3px] ' +
  'before:rounded-full before:bg-brand'
</script>

<template>
  <nav class="flex flex-col border-r border-line bg-canvas" aria-label="Main">
    <div class="px-5 pt-6 pb-5">
      <AppLogo />
      <p class="mt-1.5 text-[11px] font-medium tracking-wider text-ink-subtle uppercase">Monitoring</p>
    </div>

    <div class="flex-1 overflow-y-auto px-3 pb-3">
      <template v-for="(section, index) in sections" :key="section.title">
        <p
          :id="`nav-${index}`"
          class="px-3 pt-5 pb-1.5 text-[11px] font-medium tracking-wider text-ink-subtle uppercase"
        >
          {{ section.title }}
        </p>
        <ul class="flex flex-col gap-0.5" :aria-labelledby="`nav-${index}`">
          <li v-for="link in section.links" :key="link.name">
            <router-link :to="{ name: link.name }" :class="ROW" :active-class="ROW_ACTIVE">
              <component :is="link.icon" class="size-[18px] shrink-0 text-ink-muted" aria-hidden="true" />
              {{ link.label }}
            </router-link>
          </li>
        </ul>
      </template>
    </div>

    <div class="border-t border-line p-3">
      <!-- Who you are, and the way out. A tinted block rather than loose text: it is a different
           kind of thing from the navigation above it. -->
      <div class="flex items-center gap-2.5 rounded-xl bg-surface p-2.5">
        <span
          class="flex size-8 shrink-0 items-center justify-center rounded-full bg-brand text-[12px] font-medium text-ink-inverse"
          aria-hidden="true"
        >
          {{ initials(user?.display_name ?? '?') }}
        </span>
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm text-ink" :title="user?.display_name">{{ user?.display_name }}</p>
          <p class="truncate text-[12px] text-ink-muted">
            <template v-if="user">{{ kindLabel(user.kind) }} · @{{ user.username }}</template>
          </p>
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
