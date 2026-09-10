<script setup lang="ts">
import { computed } from 'vue'

import { usePlaylists } from '@/hooks/usePlaylists'
import { useSchedules } from '@/hooks/useSchedules'
import AppAlert from '@/reusables/AppAlert.vue'
import AppCard from '@/reusables/AppCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import { ALL_DAYS, DAY_BITS, WEEKDAYS, WEEKENDS } from '@/types/api'
import type { ScheduleRead } from '@/types/api'

const props = defineProps<{ deviceId: string; timezone: string }>()

const { schedules, resolution, isLoading, error } = useSchedules(props.deviceId)
const { items: playlists } = usePlaylists()

function dayLabel(mask: number): string {
  if (mask === ALL_DAYS) return 'Every day'
  if (mask === WEEKDAYS) return 'Weekdays'
  if (mask === WEEKENDS) return 'Weekends'
  return DAY_BITS.filter((d) => mask & d.bit).map((d) => d.short).join(', ')
}

/** "09:00:00" → "09:00". The seconds are always zero and only add noise. */
const hhmm = (t: string) => t.slice(0, 5)

/** A window whose end is at or before its start runs through midnight. */
function crossesMidnight(s: ScheduleRead) {
  return s.ends_at <= s.starts_at
}

const playlistName = (id: string) => playlists.value.find((p) => p.id === id)?.name ?? '—'

const nowPlaying = computed(() => {
  if (!resolution.value) return null
  return {
    playlist: resolution.value.playlist_id
      ? playlistName(resolution.value.playlist_id)
      : 'Nothing assigned',
    why: resolution.value.schedule_name
      ? `via schedule “${resolution.value.schedule_name}”`
      : 'the default playlist',
    // Explicit `timeZone`, not the viewer's: "on the screen" means the screen's clock, and
    // without this it silently shows whoever is looking at the CMS their own local time.
    localTime: new Date(resolution.value.device_local_time).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      timeZone: props.timezone,
    }),
  }
})
</script>

<template>
  <div class="flex flex-col gap-4">
    <div>
      <h2 class="text-lg">Schedule</h2>
      <p class="mt-0.5 text-[13px] text-ink-muted">
        Read-only — set in <router-link :to="{ name: 'campaigns' }" class="underline underline-offset-2">Campaigns</router-link>.
        Times are local to the screen ({{ timezone }}).
      </p>
    </div>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>

    <!-- The question anyone looking at a schedule actually has, answered without waiting for
         the window to come round. -->
    <AppCard v-if="nowPlaying">
      <p class="text-[13px] text-ink-muted">Playing now — {{ nowPlaying.localTime }} on the screen</p>
      <p class="mt-0.5 text-sm text-ink">
        {{ nowPlaying.playlist }}
        <span class="text-ink-muted">{{ nowPlaying.why }}</span>
      </p>
    </AppCard>

    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>

    <EmptyState
      v-else-if="!schedules.length"
      title="No schedule rules"
      description="This screen plays its default playlist around the clock, or nothing if it
                    isn't in a campaign."
    />

    <ul v-else class="flex flex-col gap-2">
      <li v-for="s in schedules" :key="s.id">
        <AppCard>
          <div class="min-w-0" :class="!s.is_enabled && 'opacity-50'">
            <p class="truncate text-sm text-ink">
              {{ s.name || playlistName(s.playlist_id) }}
              <span v-if="!s.is_enabled" class="text-ink-subtle"> · paused</span>
            </p>
            <p class="mt-0.5 text-[13px] text-ink-muted">
              {{ dayLabel(s.days_of_week) }} ·
              {{ hhmm(s.starts_at) }}–{{ hhmm(s.ends_at) }}
              <span v-if="crossesMidnight(s)" class="text-ink-subtle">(next day)</span>
              · plays {{ playlistName(s.playlist_id) }}
              <span v-if="s.priority"> · priority {{ s.priority }}</span>
            </p>
          </div>
        </AppCard>
      </li>
    </ul>
  </div>
</template>
