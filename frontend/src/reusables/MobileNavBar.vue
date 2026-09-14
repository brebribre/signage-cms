<script setup lang="ts">
/** The sidebar is `hidden` below `lg` (see SidebarView.vue) — this is what replaces it, not
 *  a second copy of it. Text-weight/colour marks the active page, the same language AppTabs
 *  uses, rather than a filled pill — one fewer visual style for the app to carry. Same icons as
 *  the sidebar, from the same list. */
import { useNavLinks } from '@/hooks/useNavLinks'

const { primary: LINKS } = useNavLinks()
</script>

<template>
  <nav
    class="flex items-stretch justify-around border-t border-line bg-canvas"
    style="padding-bottom: env(safe-area-inset-bottom)"
  >
    <router-link
      v-for="link in LINKS"
      :key="link.name"
      :to="{ name: link.name }"
      class="flex flex-1 flex-col items-center gap-0.5 px-1 py-2 text-[11px] text-ink-muted
             transition-colors duration-150"
      active-class="text-ink font-medium"
      exact-active-class="text-ink font-medium"
    >
      <component :is="link.icon" class="size-5" />
      {{ link.label }}
    </router-link>
  </nav>
</template>
