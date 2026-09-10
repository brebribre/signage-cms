<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import AppButton from '@/reusables/AppButton.vue'
import AppLogo from '@/reusables/AppLogo.vue'

const router = useRouter()
const { user, account, isOwner, logout } = useAuth()

async function onLogout() {
  await logout()
  router.push({ name: 'login' })
}

const LINKS = [
  { name: 'media', label: 'Media' },
  { name: 'playlists', label: 'Playlists' },
  { name: 'campaigns', label: 'Campaigns' },
  { name: 'devices', label: 'Devices' },
  { name: 'health', label: 'Health' },
] as const
</script>

<template>
  <!-- A divider, not an outline: the sidebar's right edge is a line between two things. -->
  <nav class="flex flex-col border-r border-line bg-canvas px-3 py-5">
    <AppLogo class="mb-6 px-2" />

    <ul class="flex flex-col gap-0.5">
      <li v-for="link in LINKS" :key="link.name">
        <router-link
          :to="{ name: link.name }"
          class="block rounded-lg px-2.5 py-1.5 text-sm transition-colors duration-150"
          active-class="bg-raised font-medium text-ink"
          exact-active-class="bg-raised font-medium text-ink"
          :class="'text-ink-muted hover:bg-surface hover:text-ink'"
        >
          {{ link.label }}
        </router-link>
      </li>
      <li v-if="isOwner">
        <router-link
          :to="{ name: 'settings-users' }"
          class="block rounded-lg px-2.5 py-1.5 text-sm text-ink-muted transition-colors
                 duration-150 hover:bg-surface hover:text-ink"
          active-class="bg-raised font-medium text-ink"
        >
          Users
        </router-link>
      </li>
      <li v-if="isOwner">
        <router-link
          :to="{ name: 'settings-updates' }"
          class="block rounded-lg px-2.5 py-1.5 text-sm text-ink-muted transition-colors
                 duration-150 hover:bg-surface hover:text-ink"
          active-class="bg-raised font-medium text-ink"
        >
          Player updates
        </router-link>
      </li>
      <li>
        <a
          href="https://docs-production-9a3e.up.railway.app"
          target="_blank"
          rel="noopener noreferrer"
          class="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm text-ink-muted
                 transition-colors duration-150 hover:bg-surface hover:text-ink"
        >
          Documentation
          <span aria-hidden="true" class="text-ink-subtle">&#8599;</span>
        </a>
      </li>
    </ul>

    <div class="mt-auto border-t border-line pt-4">
      <p class="truncate px-2.5 text-sm text-ink">{{ user?.display_name }}</p>
      <p class="truncate px-2.5 text-[13px] text-ink-muted">{{ account?.name }}</p>
      <AppButton variant="ghost" size="sm" class="mt-2 w-full" @click="onLogout">
        Sign out
      </AppButton>
    </div>
  </nav>
</template>
