<script setup lang="ts">
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'

defineProps<{ title: string; phase: string }>()
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle :title="title" />
    <EmptyState :title="`${title} arrive in ${phase}`" description="Not built yet." />
  </div>
</template>
