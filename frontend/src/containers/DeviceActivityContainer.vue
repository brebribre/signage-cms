<script setup lang="ts">
import { computed, ref } from 'vue'

import { useDeviceActivity } from '@/hooks/useDeviceActivity'
import { useFormat } from '@/hooks/useFormat'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppTabs from '@/reusables/AppTabs.vue'

const props = defineProps<{ deviceId: string }>()
const { events, plays, isLoading, error, refresh } = useDeviceActivity(props.deviceId)
const { relativeTime, duration } = useFormat()

const tab = ref<'plays' | 'events'>('plays')
const TABS = computed(() => [
  { value: 'plays', label: 'What played' },
  { value: 'events', label: 'Errors', badge: events.value.length || undefined },
])
</script>

<template>
  <div class="flex flex-col gap-3">
    <div class="flex items-center justify-between gap-4">
      <AppTabs :items="TABS" v-model="tab" />
      <AppButton variant="ghost" size="sm" :loading="isLoading" @click="refresh">Refresh</AppButton>
    </div>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>

    <template v-if="tab === 'plays'">
      <p v-if="!plays.length" class="text-sm text-ink-muted">
        Nothing reported yet. A screen sends what it played on its next heartbeat.
      </p>
      <ul v-else class="flex flex-col divide-y divide-line">
        <li v-for="p in plays" :key="p.id" class="flex items-center justify-between gap-3 py-2">
          <span class="min-w-0 truncate text-sm text-ink">
            {{ p.filename || 'Unknown file' }}
            <!-- The record outlives the file: media_id is nulled on delete but the name is
                 kept, which is the whole point of a proof-of-play log. -->
            <span v-if="!p.media_id" class="text-ink-subtle"> · deleted since</span>
          </span>
          <span class="shrink-0 text-[13px] text-ink-muted">
            {{ duration(p.seconds) }} · {{ relativeTime(p.started_at) }}
          </span>
        </li>
      </ul>
    </template>

    <template v-else>
      <p v-if="!events.length" class="text-sm text-ink-muted">No errors reported.</p>
      <ul v-else class="flex flex-col divide-y divide-line">
        <li v-for="e in events" :key="e.id" class="flex items-start justify-between gap-3 py-2">
          <span class="min-w-0 text-sm" :class="e.level === 'error' ? 'text-danger' : 'text-ink'">
            {{ e.message }}
          </span>
          <span class="shrink-0 text-[13px] text-ink-muted">{{ relativeTime(e.created_at) }}</span>
        </li>
      </ul>
    </template>
  </div>
</template>
