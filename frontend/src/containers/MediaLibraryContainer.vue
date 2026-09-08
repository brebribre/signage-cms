<script setup lang="ts">
import { useAuth } from '@/hooks/useAuth'
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'

const { account } = useAuth()
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle title="Media" :subtitle="account?.name" />
    <EmptyState
      title="The library arrives in Phase 6"
      description="Uploads land here once the R2 pipeline is built."
    />
  </div>
</template>
