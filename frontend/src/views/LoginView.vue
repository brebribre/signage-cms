<script setup lang="ts">
import AuthContainer from '@/containers/AuthContainer.vue'
import AppLogo from '@/reusables/AppLogo.vue'
</script>

<template>
  <div class="flex min-h-full items-center justify-center bg-canvas px-4 py-12">
    <div class="w-full max-w-sm">
      <AppLogo class="mb-8 block" />
      <AuthContainer />
    </div>
  </div>
</template>
