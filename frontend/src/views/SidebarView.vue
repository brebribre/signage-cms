<script setup lang="ts">
import SidebarContainer from '@/containers/SidebarContainer.vue'
</script>

<template>
  <div class="flex h-full bg-canvas">
    <SidebarContainer class="hidden w-60 shrink-0 lg:flex" />
    <main class="min-w-0 flex-1 overflow-y-auto">
      <div class="mx-auto max-w-5xl px-4 py-8 sm:px-8">
        <router-view />
      </div>
    </main>
  </div>
</template>
