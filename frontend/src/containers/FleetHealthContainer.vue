<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useFleetHealth } from '@/hooks/useFleetHealth'
import { useFormat } from '@/hooks/useFormat'
import AppAlert from '@/reusables/AppAlert.vue'
import AppCard from '@/reusables/AppCard.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import StatusDot from '@/reusables/StatusDot.vue'

const router = useRouter()
const { devices, storage, offline, withErrors, isLoading, error } = useFleetHealth()
const { bytes, relativeTime } = useFormat()

function quotaPercent(used: number, quota: number | null): number | null {
  return quota ? Math.min(100, Math.round((used / quota) * 100)) : null
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle title="Health" subtitle="Every screen, refreshed automatically" />

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>

    <!-- The two numbers worth surfacing before the list: how many screens are down, and how
         many are complaining. Everything else is detail. -->
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <AppCard>
        <p class="text-[13px] text-ink-muted">Screens</p>
        <p class="mt-0.5 text-2xl">{{ devices.length }}</p>
      </AppCard>
      <AppCard>
        <p class="text-[13px] text-ink-muted">Offline</p>
        <p class="mt-0.5 text-2xl" :class="offline.length ? 'text-danger' : 'text-ink'">
          {{ offline.length }}
        </p>
      </AppCard>
      <AppCard>
        <p class="text-[13px] text-ink-muted">Reporting errors</p>
        <p class="mt-0.5 text-2xl" :class="withErrors.length ? 'text-danger' : 'text-ink'">
          {{ withErrors.length }}
        </p>
      </AppCard>
      <AppCard>
        <p class="text-[13px] text-ink-muted">Storage</p>
        <p class="mt-0.5 text-2xl">{{ storage ? bytes(storage.used_bytes) : '—' }}</p>
        <p v-if="storage?.quota_bytes" class="text-[13px] text-ink-muted">
          of {{ bytes(storage.quota_bytes) }}
          ({{ quotaPercent(storage.used_bytes, storage.quota_bytes) }}%)
        </p>
        <p v-else-if="storage" class="text-[13px] text-ink-subtle">no quota set</p>
      </AppCard>
    </div>

    <p v-if="isLoading && !devices.length" class="text-sm text-ink-muted">Loading…</p>

    <EmptyState
      v-else-if="!devices.length"
      title="No screens yet"
      description="Pair a device and it will appear here."
    />

    <ul v-else class="flex flex-col gap-2">
      <li v-for="d in devices" :key="d.device_id">
        <AppCard interactive @click="router.push({ name: 'device-detail', params: { id: d.device_id } })">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="min-w-0">
              <p class="truncate text-base text-ink">{{ d.name }}</p>
              <p class="mt-0.5 text-[13px] text-ink-muted">
                last seen {{ relativeTime(d.last_seen_at) }}
                <span v-if="d.app_version"> · v{{ d.app_version }}</span>
                <span v-if="d.plays_24h"> · {{ d.plays_24h }} plays in 24h</span>
              </p>
            </div>
            <div class="flex shrink-0 items-center gap-4">
              <span v-if="d.error_count_24h" class="text-[13px] text-danger">
                {{ d.error_count_24h }} error{{ d.error_count_24h === 1 ? '' : 's' }}
              </span>
              <StatusDot :last-seen-at="d.last_seen_at" />
            </div>
          </div>
        </AppCard>
      </li>
    </ul>
  </div>
</template>
