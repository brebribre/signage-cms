<script setup lang="ts">
/**
 * One campaign as a card: its name, how many screens and playlists it holds, and — when the
 * caller knows — how many of its screens it is actually on right now. The same card on the
 * Campaigns list and the Overview's Now playing tab, so a campaign reads the same in both.
 */
import IconPlayArrow from '~icons/material-symbols/play-arrow'
import IconTv from '~icons/material-symbols/tv-outline'

import { useFormat } from '@/hooks/useFormat'
import AppCard from '@/reusables/AppCard.vue'
import type { CampaignSummary } from '@/types/api'

defineProps<{
  campaign: CampaignSummary
  /** Screens this campaign is winning on at this moment. Omit when not known. */
  playingOn?: number
}>()
const emit = defineEmits<{ open: [] }>()
const { date } = useFormat()
</script>

<template>
  <AppCard interactive @click="emit('open')">
    <div class="flex items-center justify-between gap-4">
      <div class="min-w-0">
        <p class="truncate text-base text-ink">{{ campaign.name }}</p>
        <div class="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-ink-muted">
          <span
            class="flex items-center gap-1 tabular-nums"
            :title="`${campaign.device_count} screen${campaign.device_count === 1 ? '' : 's'}`"
          >
            <IconTv class="size-4 shrink-0" aria-hidden="true" />
            {{ campaign.device_count }}
            <span class="sr-only">screen{{ campaign.device_count === 1 ? '' : 's' }}</span>
          </span>
          <span
            class="flex items-center gap-1 tabular-nums"
            :title="`${campaign.playlist_count} playlist${campaign.playlist_count === 1 ? '' : 's'}`"
          >
            <IconPlayArrow class="size-4 shrink-0" aria-hidden="true" />
            {{ campaign.playlist_count }}
            <span class="sr-only">playlist{{ campaign.playlist_count === 1 ? '' : 's' }}</span>
          </span>
          <span class="text-ink-subtle">Updated {{ date(campaign.updated_at) }}</span>
        </div>
      </div>
      <div class="flex shrink-0 items-center gap-3">
        <!-- Live now: on how many of its screens this campaign is the one winning. Zero is said
             in words, because a campaign nobody is showing is the thing this tab is for spotting. -->
        <span
          v-if="playingOn !== undefined"
          class="rounded-full px-2.5 py-0.5 text-[12px] tabular-nums"
          :class="playingOn > 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-raised text-ink-muted'"
        >
          {{ playingOn > 0 ? `Playing on ${playingOn} of ${campaign.device_count}` : 'Not playing now' }}
        </span>
        <span class="text-ink-subtle" aria-hidden="true">›</span>
      </div>
    </div>
  </AppCard>
</template>
