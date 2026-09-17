<script setup lang="ts">
import { useRouter } from 'vue-router'

import SidebarContainer from '@/containers/SidebarContainer.vue'
import { useAuth } from '@/hooks/useAuth'
import AppLogo from '@/reusables/AppLogo.vue'
import MobileNavBar from '@/reusables/MobileNavBar.vue'

const router = useRouter()
const { logout } = useAuth()

async function onLogout() {
  await logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="flex h-full flex-col bg-canvas lg:flex-row">
    <!-- Tab's first stop: a keyboard user can jump the whole sidebar instead of walking it on
         every page. Invisible until it has focus. -->
    <a
      href="#main"
      class="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg
             focus:bg-brand focus:px-3 focus:py-2 focus:text-sm focus:text-ink-inverse"
    >
      Skip to content
    </a>
    <SidebarContainer class="hidden w-60 shrink-0 lg:flex" />

    <!-- The sidebar carries the logo and sign-out below lg too, just hidden with it — this
         is their mobile home, not a duplicate. Page-to-page navigation is MobileNavBar,
         below the content — including owners' Settings, as a category tab there. -->
    <header
      class="flex shrink-0 items-center justify-between border-b border-line px-4 py-3 lg:hidden"
    >
      <AppLogo size="sm" />
      <div class="flex items-center gap-4">
        <button type="button" class="text-[13px] text-ink-muted" @click="onLogout">
          Sign out
        </button>
      </div>
    </header>

    <!-- The page itself is tinted and the cards on it are white — the inverse of what this app
         did before, and what gives a dashboard its layered look. The sidebar stays white so the
         content area reads as the thing you are working in. -->
    <main id="main" tabindex="-1" class="min-w-0 flex-1 overflow-y-auto bg-page">
      <div class="mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <!-- Keyed by path only where a route asks for it (see router meta.keyByPath): elsewhere
             the component is reused across param changes, as it always was. Keyed by the page's
             own route (matched[1]), not the leaf: a page whose tabs are child routes (Settings)
             then stays mounted as you switch tabs, so its tab underline slides instead of the
             whole page being rebuilt around it. -->
        <router-view v-slot="{ Component, route }">
          <component :is="Component" :key="route.meta.keyByPath ? route.path : (route.matched[1]?.name ?? route.name)" />
        </router-view>
      </div>
    </main>

    <MobileNavBar class="shrink-0 lg:hidden" />
  </div>
</template>
