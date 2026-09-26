<script setup lang="ts">
import AccountStatusContainer from '@/containers/AccountStatusContainer.vue'
import SidebarContainer from '@/containers/SidebarContainer.vue'
import MobileNavBar from '@/reusables/MobileNavBar.vue'
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
    <!-- Its own width: 240px open, a strip of icons folded (useSidebarCollapsed). -->
    <SidebarContainer class="hidden shrink-0 lg:flex" />

    <!-- Below lg there is no top bar: the page gets the whole height. Navigation is
         MobileNavBar, below the content, and Log out is in Settings → General. -->

    <!-- The page itself is tinted and the cards on it are white — the inverse of what this app
         did before, and what gives a dashboard its layered look. The sidebar stays white so the
         content area reads as the thing you are working in. -->
    <main id="main" tabindex="-1" class="min-w-0 flex-1 overflow-y-auto bg-page">
      <div class="mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <!-- Expired, or about to: said on every page, above whatever the page is. -->
        <AccountStatusContainer />
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
