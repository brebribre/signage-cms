<script setup lang="ts">
/**
 * Settings: one page, its sections as tabs. Everyone gets General (Log out lives there); the
 * rest is owner-only.
 *
 * Each tab is its own route (/settings/users, /settings/updates) rendered in the router-view
 * below, not local state — so a tab can be linked to, survives a reload, and Back steps between
 * tabs the way it steps between pages. Adding a section is a child route plus an entry here.
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from '@/hooks/useAuth'
import AppTabs from '@/reusables/AppTabs.vue'
import PageTitle from '@/reusables/PageTitle.vue'

const route = useRoute()
const router = useRouter()

const { isOwner } = useAuth()

const ALL_TABS = [
  { value: 'settings-general', label: 'General', ownerOnly: false },
  { value: 'settings-users', label: 'User management', ownerOnly: true },
  { value: 'settings-limits', label: 'Plan & limits', ownerOnly: false },
]
const tabs = computed(() => ALL_TABS.filter((t) => isOwner.value || !t.ownerOnly))

const current = computed(() => String(route.name ?? tabs.value[0].value))

function open(name: string) {
  if (name !== current.value) router.push({ name })
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle
      title="Settings"
      :subtitle="isOwner ? 'Account defaults, your team, and what your plan allows.' : undefined"
    />
    <!-- One tab is no choice at all. -->
    <AppTabs v-if="tabs.length > 1" :items="tabs" :model-value="current" @update:model-value="open" />
    <router-view />
  </div>
</template>
