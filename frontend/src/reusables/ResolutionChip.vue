<script setup lang="ts">
import { computed } from 'vue'
import type { RouteLocationRaw } from 'vue-router'

import type { DeviceResolutionRead, ResolutionRead } from '@/types/api'

/**
 * What a screen is playing right now, and why — the one rendering of this fact, used
 * everywhere a screen's resolution is shown (the fleet-wide Now view, a screen's own detail
 * page, and anywhere else a screen is referenced). Before this it was rendered three
 * slightly different ways in three places, none of which showed `valid_until` at all even
 * though the API has always returned it.
 *
 * Presentation only: `resolution` carries ids, not names, so the caller resolves
 * `playlistName`/`campaignName` from whatever playlist/campaign lists it already has loaded
 * rather than this component doing its own fetch just to render a label.
 */
const props = defineProps<{
  resolution: ResolutionRead | DeviceResolutionRead | null
  playlistName: string | null
  /** Name of the campaign responsible for the winning schedule, if any. Falls back to the
   *  schedule's own name (rarely set — campaign rules are usually left unnamed) and then to
   *  a generic label, so "via" never renders with nothing after it. */
  campaignName?: string | null
  /** Link target for the campaign name, e.g. `{ name: 'campaign-detail', params: { id } }`.
   *  Omitted (or null) renders the name as plain text — e.g. when the winning schedule
   *  predates Campaigns and has no campaign to link to. */
  campaignTo?: RouteLocationRaw | null
}>()

const viaLabel = computed(() => {
  if (!props.resolution?.schedule_id) return null
  return props.campaignName || props.resolution.schedule_name || 'a schedule'
})

/** "until 5:00 PM" today, "until Sep 20, 5:00 PM" any other day — the distinction that
 *  matters is whether reading just the time would be ambiguous about which day it means. */
const untilLabel = computed(() => {
  if (!props.resolution?.valid_until) return null
  const d = new Date(props.resolution.valid_until)
  const sameDay = d.toDateString() === new Date().toDateString()
  return sameDay
    ? d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
    : d.toLocaleString(undefined, {
        month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
      })
})
</script>

<template>
  <p v-if="!resolution || !resolution.playlist_id" class="text-[13px] text-ink-muted">
    No playlist assigned
  </p>
  <p v-else class="truncate text-[13px] text-ink-muted">
    <span class="text-ink">{{ playlistName ?? '—' }}</span>
    <template v-if="viaLabel">
      · via
      <router-link
        v-if="campaignTo"
        :to="campaignTo"
        class="text-ink underline underline-offset-2 hover:no-underline"
        @click.stop
      >{{ viaLabel }}</router-link>
      <span v-else class="text-ink">{{ viaLabel }}</span>
    </template>
    <span v-if="untilLabel"> · until {{ untilLabel }}</span>
  </p>
</template>
