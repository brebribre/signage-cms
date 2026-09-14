<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import IconChevronRight from '~icons/material-symbols/chevron-right'
import IconLogout from '~icons/material-symbols/logout'
import IconMenuBook from '~icons/material-symbols/menu-book-outline'
import IconOpenInNew from '~icons/material-symbols/open-in-new'
import IconSettings from '~icons/material-symbols/settings-outline'

import { useAuth } from '@/hooks/useAuth'
import { useNavLinks } from '@/hooks/useNavLinks'
import AppLogo from '@/reusables/AppLogo.vue'

const route = useRoute()
const router = useRouter()
const { user, account, isOwner, logout } = useAuth()
const { sections } = useNavLinks()

/** Owner-only, grouped under one collapsible Settings row rather than two more top-level links. */
const SETTINGS = [
  { name: 'settings-users', label: 'Users' },
  { name: 'settings-updates', label: 'Player updates' },
] as const

const inSettings = computed(() => String(route.name ?? '').startsWith('settings-'))
// Starts open when landing on a settings page, so the current page is never hidden.
const settingsOpen = ref(inSettings.value)

async function onLogout() {
  await logout()
  router.push({ name: 'login' })
}

const LINK =
  'flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-sm text-ink-muted transition-colors duration-150 ' +
  'hover:bg-surface hover:text-ink'
</script>

<template>
  <!-- A divider, not an outline: the sidebar's right edge is a line between two things. -->
  <nav class="flex flex-col border-r border-line bg-canvas">
    <div class="border-b border-line px-5 py-5">
      <AppLogo />
    </div>

    <div class="flex-1 overflow-y-auto px-3 py-3">
      <template v-for="section in sections" :key="section.title ?? 'top'">
        <p v-if="section.title" class="px-2.5 pt-5 pb-1.5 text-[12px] text-ink-subtle">{{ section.title }}</p>
        <ul class="flex flex-col gap-0.5">
          <li v-for="link in section.links" :key="link.name">
            <router-link :to="{ name: link.name }" :class="LINK" active-class="bg-raised text-ink">
              <component :is="link.icon" class="size-[18px] shrink-0" />
              {{ link.label }}
            </router-link>
          </li>
        </ul>
      </template>

      <template v-if="isOwner">
        <p class="px-2.5 pt-5 pb-1.5 text-[12px] text-ink-subtle">Account</p>
        <button
          type="button"
          class="w-full text-left"
          :class="[LINK, inSettings && 'text-ink']"
          :aria-expanded="settingsOpen"
          @click="settingsOpen = !settingsOpen"
        >
          <IconSettings class="size-[18px] shrink-0" />
          <span class="flex-1">Settings</span>
          <IconChevronRight
            class="size-4 shrink-0 text-ink-subtle transition-transform duration-200"
            :class="settingsOpen && 'rotate-90'"
          />
        </button>
        <ul v-if="settingsOpen" class="mt-0.5 ml-[19px] flex flex-col gap-0.5 border-l border-line pl-2">
          <li v-for="link in SETTINGS" :key="link.name">
            <router-link
              :to="{ name: link.name }"
              class="block rounded-lg px-2.5 py-1.5 text-sm text-ink-muted transition-colors duration-150
                     hover:bg-surface hover:text-ink"
              active-class="bg-raised text-ink"
            >
              {{ link.label }}
            </router-link>
          </li>
        </ul>
      </template>
    </div>

    <div class="border-t border-line px-3 py-3">
      <a
        href="https://docs-production-9a3e.up.railway.app"
        target="_blank"
        rel="noopener noreferrer"
        :class="LINK"
      >
        <IconMenuBook class="size-[18px] shrink-0" />
        <span class="flex-1">Documentation</span>
        <IconOpenInNew class="size-3.5 shrink-0 text-ink-subtle" aria-hidden="true" />
      </a>
      <div class="mt-2 flex items-center gap-2 pl-2.5">
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm text-ink">{{ user?.display_name }}</p>
          <p class="truncate text-[13px] text-ink-muted">{{ account?.name }}</p>
        </div>
        <button
          type="button"
          class="shrink-0 rounded-lg p-1.5 text-ink-muted transition-colors duration-150 hover:bg-surface hover:text-ink"
          title="Sign out"
          aria-label="Sign out"
          @click="onLogout"
        >
          <IconLogout class="size-[18px]" />
        </button>
      </div>
    </div>
  </nav>
</template>
