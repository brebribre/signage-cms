<script setup lang="ts">
/**
 * Settings: one page, its sections as tabs. Owner-only, like everything in it.
 *
 * Each tab is its own route (/settings/users, /settings/updates) rendered in the router-view
 * below, not local state — so a tab can be linked to, survives a reload, and Back steps between
 * tabs the way it steps between pages. Adding a section is a child route plus an entry here.
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppTabs from '@/reusables/AppTabs.vue'
import PageTitle from '@/reusables/PageTitle.vue'

const route = useRoute()
const router = useRouter()

const TABS = [
  { value: 'settings-general', label: 'General' },
  { value: 'settings-users', label: 'User management' },
  { value: 'settings-updates', label: 'Software updates' },
] as const

const current = computed(() => String(route.name ?? TABS[0].value))

function open(name: string) {
  if (name !== current.value) router.push({ name })
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle title="Settings" subtitle="Account defaults, your team, and the player software on your screens." />
    <AppTabs :items="TABS" :model-value="current" @update:model-value="open" />
    <router-view />
  </div>
</template>
