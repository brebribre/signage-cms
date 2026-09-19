<script setup lang="ts">
import { useRouter } from 'vue-router'
import IconAdd from '~icons/material-symbols/add'

import { useCampaigns } from '@/hooks/useCampaigns'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import CampaignCard from '@/reusables/CampaignCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import ListRowSkeleton from '@/reusables/ListRowSkeleton.vue'
import SkeletonList from '@/reusables/SkeletonList.vue'

const router = useRouter()
const { items, isLoading, error } = useCampaigns()
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle
      title="Campaigns"
      :subtitle="`${items.length} campaign${items.length === 1 ? '' : 's'}`"
    >
      <template #actions>
        <AppButton size="sm" @click="router.push({ name: 'deploy' })">
          <IconAdd class="size-4" aria-hidden="true" />
          New campaign
        </AppButton>
      </template>
    </PageTitle>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <SkeletonList v-if="isLoading" label="Loading campaigns">
      <ListRowSkeleton />
    </SkeletonList>

    <EmptyState
      v-else-if="!items.length"
      title="No campaigns yet"
      description="A campaign assigns one or more playlists, each on its own schedule, to
                    every screen you pick — the only place playlist assignment happens."
    >
      <template #actions>
        <AppButton size="sm" @click="router.push({ name: 'deploy' })">
          <IconAdd class="size-4" aria-hidden="true" />
          New campaign
        </AppButton>
      </template>
    </EmptyState>

    <div v-else class="flex flex-col gap-2">
      <CampaignCard
        v-for="c in items" :key="c.id" :campaign="c"
        @open="router.push({ name: 'campaign-detail', params: { id: c.id } })"
      />
    </div>
  </div>
</template>
