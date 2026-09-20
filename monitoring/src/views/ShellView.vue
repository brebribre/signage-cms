<script setup lang="ts">
/**
 * The console's frame: one bar across the top with the logo, the pages, who you are, and the
 * way out. A bar rather than the CMS's sidebar because there is one page today and the
 * people here are staff, not customers — when monitoring grows (fleet health, crash reports
 * across every account), the pages just line up along the bar.
 */
import { useRouter } from 'vue-router'
import IconCorporate from '~icons/material-symbols/corporate-fare'
import IconLogout from '~icons/material-symbols/logout'

import { useAuth } from '@/hooks/useAuth'
import AppLogo from '@/reusables/AppLogo.vue'

const router = useRouter()
const { user, logout } = useAuth()

const links = [{ name: 'accounts', label: 'Accounts', icon: IconCorporate }]

async function onLogout() {
  await logout()
  router.push({ name: 'login' })
}

const LINK =
  'flex h-14 items-center gap-2 border-b-2 border-transparent px-1 text-sm text-ink-muted transition-colors ' +
  'duration-150 hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-bright'
/** The current page: weight and a bar under it, not colour alone. */
const LINK_ACTIVE = '!border-brand !text-brand font-medium [&_svg]:text-brand'
</script>

<template>
  <div class="flex h-full flex-col bg-page">
    <a
      href="#main"
      class="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg
             focus:bg-brand focus:px-3 focus:py-2 focus:text-sm focus:text-ink-inverse"
    >
      Skip to content
    </a>

    <header class="shrink-0 border-b border-line bg-canvas">
      <div class="mx-auto flex max-w-5xl items-center gap-6 px-4 sm:px-8">
        <div class="flex items-center gap-2.5 py-3">
          <AppLogo size="sm" />
          <span class="text-[11px] font-medium tracking-wider text-ink-subtle uppercase">Monitoring</span>
        </div>

        <nav class="flex items-center gap-4" aria-label="Main">
          <router-link
            v-for="link in links"
            :key="link.name"
            :to="{ name: link.name }"
            :class="LINK"
            :active-class="LINK_ACTIVE"
          >
            <component :is="link.icon" class="size-[18px] shrink-0" aria-hidden="true" />
            {{ link.label }}
          </router-link>
        </nav>

        <div class="ml-auto flex items-center gap-2">
          <span class="hidden truncate text-sm text-ink-muted sm:block" :title="user?.username">
            {{ user?.display_name }}
          </span>
          <button
            type="button"
            class="rounded-lg p-1.5 text-ink-muted transition-colors duration-150 hover:bg-raised hover:text-ink
                   focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-bright"
            title="Sign out"
            aria-label="Sign out"
            @click="onLogout"
          >
            <IconLogout class="size-[18px]" aria-hidden="true" />
          </button>
        </div>
      </div>
    </header>

    <main id="main" tabindex="-1" class="min-w-0 flex-1 overflow-y-auto">
      <div class="mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <router-view />
      </div>
    </main>
  </div>
</template>
