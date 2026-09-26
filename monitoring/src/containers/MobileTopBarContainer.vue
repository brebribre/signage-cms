<script setup lang="ts">
/**
 * Navigation below `lg`, where the sidebar would take too much of the screen: a slim bar across
 * the top with the logo, the page you are on, and a menu button. The menu drops down under the
 * bar with the same pages as the sidebar (useNavLinks), then who is signed in and the way out.
 *
 * It closes on a page change, a tap on the dimmed page, or Escape — whichever comes first.
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import IconClose from '~icons/material-symbols/close'
import IconLogout from '~icons/material-symbols/logout'
import IconMenu from '~icons/material-symbols/menu'

import { initials } from '@/hooks/useAccountMarks'
import { useAuth } from '@/hooks/useAuth'
import { useNavLinks } from '@/hooks/useNavLinks'
import { useStaffRights } from '@/hooks/useStaffRights'
import AppLogo from '@/reusables/AppLogo.vue'

const route = useRoute()
const router = useRouter()
const { user, logout } = useAuth()
const { label: kindLabel } = useStaffRights()
const { sections } = useNavLinks()

const open = ref(false)

/** The page you are on, named beside the logo so the bar says where you are without opening it. */
const current = computed(
  () => sections.flatMap((s) => s.links).find((l) => route.matched.some((m) => m.name === l.name)) ?? null,
)

watch(() => route.fullPath, () => (open.value = false))

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') open.value = false
}
onMounted(() => document.addEventListener('keydown', onKey))
onUnmounted(() => document.removeEventListener('keydown', onKey))

async function onLogout() {
  open.value = false
  await logout()
  router.push({ name: 'login' })
}

const ROW =
  'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-[15px] text-ink transition-colors ' +
  'duration-150 hover:bg-surface focus-visible:outline-2 focus-visible:outline-offset-2 ' +
  'focus-visible:outline-brand-bright'
const ROW_ACTIVE =
  'relative bg-brand-soft hover:!bg-brand-soft !text-brand font-medium [&_svg]:!text-brand ' +
  'before:absolute before:left-0 before:top-2 before:bottom-2 before:w-[3px] ' +
  'before:rounded-full before:bg-brand'
</script>

<template>
  <header class="relative z-30 border-b border-line bg-canvas">
    <div class="flex h-14 items-center gap-3 px-4">
      <router-link :to="{ name: 'accounts' }" class="shrink-0" aria-label="Marien Monitoring, home">
        <AppLogo size="sm" />
      </router-link>
      <span v-if="current" class="flex min-w-0 items-center gap-1.5 border-l border-line pl-3 text-sm text-ink-muted">
        <component :is="current.icon" class="size-4 shrink-0" aria-hidden="true" />
        <span class="truncate">{{ current.label }}</span>
      </span>
      <button
        type="button"
        class="-mr-1.5 ml-auto rounded-lg p-2 text-ink transition-colors duration-150 hover:bg-raised
               focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-bright"
        :aria-expanded="open"
        aria-controls="mobile-menu"
        :aria-label="open ? 'Close menu' : 'Open menu'"
        @click="open = !open"
      >
        <IconClose v-if="open" class="size-6" aria-hidden="true" />
        <IconMenu v-else class="size-6" aria-hidden="true" />
      </button>
    </div>

    <template v-if="open">
      <!-- The page underneath, dimmed: a tap on it closes the menu. -->
      <div class="fixed inset-x-0 top-14 bottom-0 animate-fade-in bg-ink/30 motion-reduce:animate-none"
           aria-hidden="true" @click="open = false" />
      <nav
        id="mobile-menu"
        class="menu absolute inset-x-0 top-full max-h-[calc(100dvh_-_3.5rem)] overflow-y-auto rounded-b-2xl
               border-b border-line bg-canvas px-3 pb-3"
        aria-label="Main"
      >
        <template v-for="(section, index) in sections" :key="section.title">
          <p :id="`m-nav-${index}`" class="px-3 pt-4 pb-1.5 text-[11px] font-medium tracking-wider text-ink-subtle uppercase">
            {{ section.title }}
          </p>
          <ul class="flex flex-col gap-0.5" :aria-labelledby="`m-nav-${index}`">
            <li v-for="link in section.links" :key="link.name">
              <router-link :to="{ name: link.name }" :class="ROW" :active-class="ROW_ACTIVE">
                <component :is="link.icon" class="size-5 shrink-0 text-ink-muted" aria-hidden="true" />
                {{ link.label }}
              </router-link>
            </li>
          </ul>
        </template>

        <div class="mt-4 flex items-center gap-2.5 rounded-xl bg-surface p-2.5">
          <span
            class="flex size-9 shrink-0 items-center justify-center rounded-full bg-brand text-[12px] font-medium text-ink-inverse"
            aria-hidden="true"
          >
            {{ initials(user?.display_name ?? '?') }}
          </span>
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm text-ink">{{ user?.display_name }}</p>
            <p class="truncate text-[12px] text-ink-muted">
              <template v-if="user">{{ kindLabel(user.kind) }} · @{{ user.username }}</template>
            </p>
          </div>
          <button
            type="button"
            class="flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm text-ink-muted transition-colors
                   duration-150 hover:bg-raised hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2
                   focus-visible:outline-brand-bright"
            @click="onLogout"
          >
            <IconLogout class="size-[18px]" aria-hidden="true" />
            Sign out
          </button>
        </div>
      </nav>
    </template>
  </header>
</template>

<style scoped>
.menu {
  animation: menu-down 240ms cubic-bezier(0.32, 0.72, 0, 1);
}
@keyframes menu-down {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
}
@media (prefers-reduced-motion: reduce) {
  .menu {
    animation: none;
  }
}
</style>
