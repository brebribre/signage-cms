<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AuthContainer from '@/containers/AuthContainer.vue'
import AppLogo from '@/reusables/AppLogo.vue'

const route = useRoute()
const mode = computed(() => (route.name === 'signup' ? 'signup' : 'login'))
</script>

<template>
  <div class="flex min-h-full items-center justify-center bg-canvas px-4 py-12">
    <div class="w-full max-w-sm">
      <AppLogo class="mb-8 block" />
      <AuthContainer :mode="mode" />
    </div>
  </div>
</template>
