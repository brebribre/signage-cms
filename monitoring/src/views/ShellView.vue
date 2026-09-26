<script setup lang="ts">
/**
 * The console's frame, laid out like the CMS's (frontend/src/views/SidebarView.vue): a sidebar
 * down the left from `lg` up, and below that a slim bar across the top whose menu holds the same
 * pages. Both read their links from useNavLinks, so they can never disagree.
 */
import MobileTopBarContainer from '@/containers/MobileTopBarContainer.vue'
import SidebarContainer from '@/containers/SidebarContainer.vue'
</script>

<template>
  <div class="flex h-full flex-col bg-canvas lg:flex-row">
    <!-- Tab's first stop: a keyboard user can skip the navigation instead of walking it on every
         page. Invisible until it has focus. -->
    <a
      href="#main"
      class="sr-only focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50 focus:rounded-lg
             focus:bg-brand focus:px-3 focus:py-2 focus:text-sm focus:text-ink-inverse"
    >
      Skip to content
    </a>

    <SidebarContainer class="hidden w-60 shrink-0 lg:flex" />
    <MobileTopBarContainer class="shrink-0 lg:hidden" />

    <!-- The page is tinted and the cards on it white; the sidebar stays white, so the content
         area reads as the thing you are working in. -->
    <main id="main" tabindex="-1" class="min-w-0 flex-1 overflow-y-auto bg-page">
      <div class="mx-auto max-w-5xl px-4 py-6 sm:px-8 sm:py-8">
        <router-view />
      </div>
    </main>
  </div>
</template>
