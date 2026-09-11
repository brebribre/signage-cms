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
    <SidebarContainer class="hidden w-60 shrink-0 lg:flex" />

    <!-- The sidebar carries the logo and sign-out below lg too, just hidden with it — this
         is their mobile home, not a duplicate. Page-to-page navigation is MobileNavBar,
         below the content. -->
    <header
      class="flex shrink-0 items-center justify-between border-b border-line px-4 py-3 lg:hidden"
    >
      <AppLogo size="sm" />
      <button type="button" class="text-[13px] text-ink-muted" @click="onLogout">Sign out</button>
    </header>

    <main class="min-w-0 flex-1 overflow-y-auto">
      <div class="mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <router-view />
      </div>
    </main>

    <MobileNavBar class="shrink-0 lg:hidden" />
  </div>
</template>
