<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useCampaigns } from '@/hooks/useCampaigns'
import { useFormat } from '@/hooks/useFormat'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'

const router = useRouter()
const { items, isLoading, error } = useCampaigns()
const { date } = useFormat()
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle
      title="Campaigns"
      :subtitle="`${items.length} campaign${items.length === 1 ? '' : 's'}`"
    >
      <template #actions>
        <AppButton size="sm" @click="router.push({ name: 'campaign-new' })">
          New campaign
        </AppButton>
      </template>
    </PageTitle>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>

    <EmptyState
      v-else-if="!items.length"
      title="No campaigns yet"
      description="A campaign assigns one or more playlists, each on its own schedule, to
                    every screen you pick — the only place playlist assignment happens."
    >
      <template #actions>
        <AppButton size="sm" @click="router.push({ name: 'campaign-new' })">
          New campaign
        </AppButton>
      </template>
    </EmptyState>

    <div v-else class="flex flex-col gap-2">
      <AppCard
        v-for="c in items"
        :key="c.id"
        interactive
        @click="router.push({ name: 'campaign-detail', params: { id: c.id } })"
      >
        <div class="flex items-center justify-between gap-4">
          <div class="min-w-0">
            <p class="truncate text-base text-ink">{{ c.name }}</p>
            <p class="mt-0.5 text-[13px] text-ink-muted">
              {{ c.device_count }} screen{{ c.device_count === 1 ? '' : 's' }} ·
              {{ c.rule_count }} rule{{ c.rule_count === 1 ? '' : 's' }} ·
              updated {{ date(c.updated_at) }}
            </p>
          </div>
          <span class="shrink-0 text-ink-subtle" aria-hidden="true">›</span>
        </div>
      </AppCard>
    </div>
  </div>
</template>
