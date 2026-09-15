<script setup lang="ts">
import { useRouter } from 'vue-router'
import IconPlayArrow from '~icons/material-symbols/play-arrow'
import IconTv from '~icons/material-symbols/tv-outline'

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
        <AppButton size="sm" @click="router.push({ name: 'deploy' })">New campaign</AppButton>
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
        <AppButton size="sm" @click="router.push({ name: 'deploy' })">New campaign</AppButton>
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
            <div class="mt-1 flex items-center gap-4 text-[13px] text-ink-muted">
              <span
                class="flex items-center gap-1 tabular-nums"
                :title="`${c.device_count} screen${c.device_count === 1 ? '' : 's'}`"
              >
                <IconTv class="size-4 shrink-0" aria-hidden="true" />
                {{ c.device_count }}
                <span class="sr-only">screen{{ c.device_count === 1 ? '' : 's' }}</span>
              </span>
              <span
                class="flex items-center gap-1 tabular-nums"
                :title="`${c.playlist_count} playlist${c.playlist_count === 1 ? '' : 's'}`"
              >
                <IconPlayArrow class="size-4 shrink-0" aria-hidden="true" />
                {{ c.playlist_count }}
                <span class="sr-only">playlist{{ c.playlist_count === 1 ? '' : 's' }}</span>
              </span>
              <span class="text-ink-subtle">Updated {{ date(c.updated_at) }}</span>
            </div>
          </div>
          <span class="shrink-0 text-ink-subtle" aria-hidden="true">›</span>
        </div>
      </AppCard>
    </div>
  </div>
</template>
