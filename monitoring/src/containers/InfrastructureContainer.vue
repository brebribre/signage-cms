<script setup lang="ts">
/**
 * The platform in numbers: how full the R2 bucket is against the line where we upgrade, how
 * many people can sign in, and how many screens are paired and online.
 *
 * Laid out as a dashboard rather than a table because it is read at a glance — "do I need to do
 * anything?" — so the one reading that decides that, the bucket gauge, is the largest thing on
 * the page and says its verdict in words beside the colour.
 */
import { computed, ref } from 'vue'
import IconCloud from '~icons/material-symbols/cloud-outline'
import IconGroup from '~icons/material-symbols/group-outline'
import IconRefresh from '~icons/material-symbols/refresh'
import IconTrending from '~icons/material-symbols/trending-up'
import IconTv from '~icons/material-symbols/tv-outline'
import IconWarning from '~icons/material-symbols/warning-outline'

import { useFormat } from '@/hooks/useFormat'
import { useInfrastructure } from '@/hooks/useInfrastructure'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import SkeletonBlock from '@/reusables/SkeletonBlock.vue'
import type { StoragePart } from '@/types/api'

const { data, isLoading, error, refresh } = useInfrastructure()
const { bytes, relativeTime } = useFormat()

const CARD = 'rounded-2xl bg-canvas p-5 sm:p-6'
const LABEL = 'text-[12px] font-medium tracking-wider text-ink-muted uppercase'

// --- Storage ---------------------------------------------------------------------------------

const storage = computed(() => data.value?.storage ?? null)
const usedPct = computed(() => {
  const s = storage.value
  return s && s.limit_bytes > 0 ? (s.used_bytes / s.limit_bytes) * 100 : 0
})
const pctText = computed(() => {
  const p = usedPct.value
  return p > 0 && p < 10 ? p.toFixed(1) : String(Math.round(p))
})
const leftBytes = computed(() => (storage.value ? Math.max(0, storage.value.limit_bytes - storage.value.used_bytes) : 0))

/** The verdict. Colour and words together, never colour alone. */
const verdict = computed(() => {
  const p = usedPct.value
  if (p >= 90) return { label: 'Upgrade now', tone: 'danger' as const }
  if (p >= 70) return { label: 'Plan an upgrade', tone: 'warn' as const }
  return { label: 'Plenty of room', tone: 'good' as const }
})
const VERDICT_PILL = {
  good: 'bg-[#e8f5ec] text-good',
  warn: 'bg-[#fbf3e4] text-warn',
  danger: 'bg-[#f8eaea] text-danger',
}

// The gauge: a 270° arc with its gap at the bottom, drawn as a dashed circle.
const R = 80
const CIRC = 2 * Math.PI * R
const ARC = CIRC * 0.75
const arcFill = computed(() => ARC * Math.min(1, usedPct.value / 100))
const gaugeStroke = computed(() =>
  verdict.value.tone === 'danger' ? 'var(--color-danger)' : verdict.value.tone === 'warn' ? 'var(--color-warn)' : 'url(#gauge-blue)',
)

/** Fixed colour per part — follows the part, never its size or order on screen. Checked for
 *  colour-blind separation; the lighter two always sit beside a written label and figure. */
const PART_COLOR: Record<StoragePart['key'], string> = {
  media: '#1f55c4',
  copies: '#5aa9f5',
  thumbnails: '#13a386',
  builds: '#e0a100',
  other: '#bfbfbf',
}
const PART_HINT: Record<StoragePart['key'], string> = {
  media: 'Customer uploads',
  copies: 'Re-encoded for screens',
  thumbnails: 'Previews in the CMS',
  builds: 'Android player versions',
  other: 'Outside the usual folders',
}
const parts = computed(() => (storage.value?.parts ?? []).filter((p) => p.bytes > 0 || p.key !== 'other'))
const partsTotal = computed(() => parts.value.reduce((n, p) => n + p.bytes, 0))
function partShare(p: StoragePart) {
  return partsTotal.value ? (p.bytes / partsTotal.value) * 100 : 0
}

/** When the line is reached, at the last 30 days' pace. */
const forecast = computed(() => {
  const s = storage.value
  if (!s) return null
  if (s.used_bytes >= s.limit_bytes) return 'The line is already crossed.'
  if (s.added_30d_bytes <= 0) return 'Nothing new was uploaded in the last 30 days, so there is no pace to go by.'
  const months = leftBytes.value / s.added_30d_bytes
  const when =
    months < 1
      ? 'within a month'
      : months < 24
        ? `in about ${Math.round(months)} month${Math.round(months) === 1 ? '' : 's'}`
        : `in about ${Math.round(months / 12)} years`
  return `At ${bytes(s.added_30d_bytes)} a month, the ${bytes(s.limit_bytes)} line is reached ${when}.`
})

// --- Monthly uploads -------------------------------------------------------------------------

const monthly = computed(() => storage.value?.monthly ?? [])
const monthMax = computed(() => Math.max(1, ...monthly.value.map((m) => m.bytes)))
const hoveredMonth = ref<number | null>(null)
function monthName(m: string, long = false) {
  const [y, mo] = m.split('-').map(Number)
  return new Date(y!, mo! - 1, 1).toLocaleDateString(undefined, long ? { month: 'long', year: 'numeric' } : { month: 'short' })
}
/** Which bar carries its figure: the one under the pointer, else the current month. */
const labelledMonth = computed(() => hoveredMonth.value ?? monthly.value.length - 1)

// --- Accounts, people, screens ---------------------------------------------------------------

const topAccounts = computed(() => storage.value?.top_accounts ?? [])
const topMax = computed(() => Math.max(1, ...topAccounts.value.map((a) => a.bytes)))

const users = computed(() => data.value?.users ?? null)
const screens = computed(() => data.value?.screens ?? null)
const onlinePct = computed(() => (screens.value?.paired ? (screens.value.online / screens.value.paired) * 100 : 0))
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle title="Infrastructure" subtitle="How full the storage is, and how many people and screens use Paskall.">
      <template #actions>
        <div class="flex items-center gap-3">
          <span v-if="data" class="hidden text-[13px] text-ink-subtle sm:inline">
            Updated {{ relativeTime(data.generated_at) }}
          </span>
          <AppButton variant="secondary" size="sm" :disabled="isLoading" @click="refresh">
            <IconRefresh class="size-4" :class="isLoading && 'animate-spin'" aria-hidden="true" />
            Refresh
          </AppButton>
        </div>
      </template>
    </PageTitle>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>

    <!-- First load: the same shapes the numbers will fill, so nothing jumps when they arrive. -->
    <div v-if="!data && isLoading" class="grid gap-4 xl:grid-cols-3" aria-busy="true" aria-label="Loading">
      <div :class="[CARD, 'xl:col-span-2']"><SkeletonBlock class="h-72 w-full rounded-xl" /></div>
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
        <div :class="CARD"><SkeletonBlock class="h-32 w-full rounded-xl" /></div>
        <div :class="CARD"><SkeletonBlock class="h-32 w-full rounded-xl" /></div>
      </div>
    </div>

    <template v-else-if="data && storage && users && screens">
      <div class="grid gap-4 xl:grid-cols-3">
        <!-- ============ Storage: the reading that decides whether to act ============ -->
        <section :class="[CARD, 'xl:col-span-2']" aria-labelledby="storage-title">
          <header class="flex flex-wrap items-center justify-between gap-2">
            <h2 id="storage-title" class="flex items-center gap-2 text-lg">
              <span class="grid size-8 place-items-center rounded-lg bg-brand-soft text-brand">
                <IconCloud class="size-[18px]" aria-hidden="true" />
              </span>
              R2 storage
            </h2>
            <span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-medium" :class="VERDICT_PILL[verdict.tone]">
              <IconWarning v-if="verdict.tone !== 'good'" class="size-3.5" aria-hidden="true" />
              <span v-else class="size-1.5 rounded-full bg-current" aria-hidden="true" />
              {{ verdict.label }}
            </span>
          </header>

          <div class="mt-4 flex flex-col items-center gap-6 sm:flex-row sm:items-center sm:gap-8">
            <!-- Gauge -->
            <div class="relative size-52 shrink-0">
              <svg viewBox="0 0 200 200" class="size-full" role="img" :aria-label="`${pctText}% of the storage line used`">
                <defs>
                  <linearGradient id="gauge-blue" x1="0" y1="1" x2="1" y2="0">
                    <stop offset="0%" stop-color="#002f96" />
                    <stop offset="100%" stop-color="#0076dd" />
                  </linearGradient>
                </defs>
                <g transform="rotate(135 100 100)">
                  <circle cx="100" cy="100" :r="R" fill="none" stroke="var(--color-raised)" stroke-width="14"
                          stroke-linecap="round" :stroke-dasharray="`${ARC} ${CIRC}`" />
                  <circle v-if="arcFill > 0" cx="100" cy="100" :r="R" fill="none" :stroke="gaugeStroke" stroke-width="14"
                          stroke-linecap="round" :stroke-dasharray="`${arcFill} ${CIRC}`"
                          class="transition-[stroke-dasharray] duration-700 ease-out" />
                </g>
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center pt-1 text-center">
                <span class="font-display text-5xl leading-none font-medium tracking-tight text-ink tabular-nums">
                  {{ pctText }}<span class="text-2xl text-ink-muted">%</span>
                </span>
                <span class="mt-2 text-[13px] text-ink-muted">used</span>
              </div>
              <span class="absolute bottom-3 left-1/2 -translate-x-1/2 text-[12px] whitespace-nowrap text-ink-subtle">
                of {{ bytes(storage.limit_bytes) }}
              </span>
            </div>

            <!-- Key figures -->
            <dl class="grid w-full grid-cols-2 gap-x-6 gap-y-5">
              <div>
                <dt :class="LABEL">Used</dt>
                <dd class="mt-1 font-display text-3xl whitespace-nowrap text-ink tabular-nums">{{ bytes(storage.used_bytes) }}</dd>
              </div>
              <div>
                <dt :class="LABEL">Space left</dt>
                <dd class="mt-1 font-display text-3xl whitespace-nowrap text-ink tabular-nums">{{ bytes(leftBytes) }}</dd>
              </div>
              <div>
                <dt :class="LABEL">Upgrade line</dt>
                <dd class="mt-1 font-display text-3xl whitespace-nowrap text-ink tabular-nums">{{ bytes(storage.limit_bytes) }}</dd>
              </div>
              <div>
                <dt :class="LABEL">Files</dt>
                <dd class="mt-1 font-display text-3xl whitespace-nowrap text-ink tabular-nums">
                  {{ storage.object_count === null ? '—' : storage.object_count.toLocaleString() }}
                </dd>
              </div>
              <p class="col-span-2 flex gap-2 rounded-xl bg-surface px-3 py-2.5 text-[13px] leading-snug text-ink-muted">
                <IconTrending class="mt-px size-4 shrink-0 text-brand" aria-hidden="true" />
                {{ forecast }}
              </p>
            </dl>
          </div>

          <!-- What the bucket holds -->
          <div class="mt-6 border-t border-line pt-5">
            <p class="sr-only">What the storage holds</p>
            <div class="flex h-3 w-full gap-[2px] overflow-hidden rounded-full bg-raised" aria-hidden="true">
              <span
                v-for="p in parts"
                v-show="p.bytes > 0"
                :key="p.key"
                class="h-full first:rounded-l-full last:rounded-r-full"
                :style="{ width: `${Math.max(partShare(p), 0.8)}%`, background: PART_COLOR[p.key] }"
                :title="`${p.label}: ${bytes(p.bytes)}`"
              />
            </div>
            <ul class="mt-4 grid gap-x-6 gap-y-3 sm:grid-cols-2">
              <li v-for="p in parts" :key="p.key" class="flex items-start gap-2.5">
                <span class="mt-1 size-2.5 shrink-0 rounded-[3px]" :style="{ background: PART_COLOR[p.key] }" aria-hidden="true" />
                <span class="min-w-0 flex-1">
                  <span class="flex items-baseline justify-between gap-2 text-sm">
                    <span class="text-ink">{{ p.label }}</span>
                    <span class="text-ink tabular-nums">{{ bytes(p.bytes) }}</span>
                  </span>
                  <span class="flex items-baseline justify-between gap-2 text-[12px] text-ink-muted">
                    <span class="truncate">{{ PART_HINT[p.key] }}</span>
                    <span class="shrink-0 tabular-nums">
                      <template v-if="p.objects !== null">{{ p.objects.toLocaleString() }} files · </template>{{ Math.round(partShare(p)) }}%
                    </span>
                  </span>
                </span>
              </li>
            </ul>
            <p class="mt-4 text-[12px] text-ink-subtle">
              <template v-if="storage.source === 'bucket'">
                Measured in the bucket itself {{ relativeTime(storage.measured_at) }} — this is what Cloudflare bills.
                R2 has no hard limit; the line is ours, set by <code class="text-ink-muted">R2_STORAGE_LIMIT_GB</code> on the backend.
              </template>
              <template v-else>{{ storage.bucket_error }}</template>
            </p>
          </div>
        </section>

        <!-- ============ Screens and people: side by side under the storage card until there
             is room for a third column, then stacked beside it. ============ -->
        <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-1 xl:content-start">
          <!-- Screens: the brand gradient, as the CMS uses on its hero cards. -->
          <section
            class="relative overflow-hidden rounded-2xl bg-linear-to-br from-brand-strong to-brand-bright p-5 text-white sm:p-6"
            aria-labelledby="screens-title"
          >
            <!-- Soft rings in the corner, for depth. Decoration only. -->
            <span class="pointer-events-none absolute -top-16 -right-16 size-48 rounded-full border-[28px] border-white/[0.06]" aria-hidden="true" />
            <h2 id="screens-title" class="flex items-center gap-2 text-base text-white/85">
              <IconTv class="size-[18px]" aria-hidden="true" />
              Connected screens
            </h2>
            <p class="mt-3 font-display text-6xl leading-none font-medium tabular-nums">{{ screens.paired }}</p>
            <p class="mt-1.5 text-[13px] text-white/70">paired across every account</p>

            <div class="mt-5">
              <div class="flex items-center justify-between text-[13px]">
                <span class="flex items-center gap-2">
                  <span class="relative flex size-2">
                    <span v-if="screens.online" class="absolute inline-flex size-full animate-ping rounded-full bg-[#7ee2a0] opacity-60 motion-reduce:hidden" />
                    <span class="relative inline-flex size-2 rounded-full" :class="screens.online ? 'bg-[#7ee2a0]' : 'bg-white/40'" />
                  </span>
                  {{ screens.online }} online now
                </span>
                <span class="text-white/70">{{ screens.paired - screens.online }} offline</span>
              </div>
              <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-white/15" aria-hidden="true">
                <div class="h-full rounded-full bg-white transition-[width] duration-700" :style="{ width: `${onlinePct}%` }" />
              </div>
            </div>

            <dl class="mt-5 grid grid-cols-3 gap-2 border-t border-white/15 pt-4 text-center">
              <div>
                <dt class="text-[11px] text-white/65">Android</dt>
                <dd class="font-display text-xl tabular-nums">{{ screens.android }}</dd>
              </div>
              <div>
                <dt class="text-[11px] text-white/65">Web</dt>
                <dd class="font-display text-xl tabular-nums">{{ screens.web }}</dd>
              </div>
              <div>
                <dt class="text-[11px] text-white/65">New, 30 days</dt>
                <dd class="font-display text-xl tabular-nums">+{{ screens.new_30d }}</dd>
              </div>
            </dl>
          </section>

          <!-- People -->
          <section :class="CARD" aria-labelledby="users-title">
            <h2 id="users-title" class="flex items-center gap-2 text-base text-ink-muted">
              <span class="grid size-8 place-items-center rounded-lg bg-brand-soft text-brand">
                <IconGroup class="size-[18px]" aria-hidden="true" />
              </span>
              Users
            </h2>
            <div class="mt-3 flex items-end justify-between gap-2">
              <p class="font-display text-5xl leading-none font-medium text-ink tabular-nums">{{ users.total }}</p>
              <span v-if="users.new_30d" class="rounded-full bg-brand-soft px-2 py-0.5 text-[12px] font-medium text-brand">
                +{{ users.new_30d }} in 30 days
              </span>
            </div>
            <p class="mt-1.5 text-[13px] text-ink-muted">
              people who can sign in<template v-if="users.total !== users.active">, {{ users.active }} active</template>
            </p>
            <dl class="mt-5 grid grid-cols-3 gap-2 border-t border-line pt-4">
              <div>
                <dt class="text-[11px] text-ink-muted">Main users</dt>
                <dd class="font-display text-xl text-ink tabular-nums">{{ users.main_users }}</dd>
              </div>
              <div>
                <dt class="text-[11px] text-ink-muted">Sub accounts</dt>
                <dd class="font-display text-xl text-ink tabular-nums">{{ users.sub_accounts }}</dd>
              </div>
              <div>
                <dt class="text-[11px] text-ink-muted">Clients</dt>
                <dd class="font-display text-xl text-ink tabular-nums">{{ users.client_accounts }}</dd>
              </div>
            </dl>
          </section>
        </div>
      </div>

      <div class="grid gap-4 xl:grid-cols-3">
        <!-- ============ Growth ============ -->
        <section :class="[CARD, 'xl:col-span-2']" aria-labelledby="growth-title">
          <header class="flex flex-wrap items-baseline justify-between gap-2">
            <h2 id="growth-title" class="text-lg">Uploads by month</h2>
            <span class="text-[12px] text-ink-muted">Files and their copies still stored, by the month they arrived</span>
          </header>
          <div class="relative mt-6 flex h-44 items-end gap-3 sm:gap-5" @mouseleave="hoveredMonth = null">
            <!-- Recessive guide at the top of the scale. -->
            <span class="pointer-events-none absolute inset-x-0 top-6 border-t border-dashed border-line" aria-hidden="true" />
            <div
              v-for="(m, i) in monthly"
              :key="m.month"
              class="group relative flex h-full flex-1 flex-col items-center justify-end"
              @mouseenter="hoveredMonth = i"
              @focus="hoveredMonth = i"
              @blur="hoveredMonth = null"
              tabindex="0"
              :aria-label="`${monthName(m.month, true)}: ${bytes(m.bytes)}`"
            >
              <span
                v-if="labelledMonth === i"
                class="mb-1.5 rounded-md px-1.5 py-0.5 text-[12px] whitespace-nowrap tabular-nums"
                :class="hoveredMonth === i ? 'bg-ink text-ink-inverse' : 'text-ink'"
              >
                {{ bytes(m.bytes) }}
              </span>
              <div class="flex w-full max-w-14 flex-1 items-end">
                <div
                  class="w-full rounded-t-[4px] transition-[height,background-color] duration-500"
                  :class="i === monthly.length - 1 ? 'bg-brand' : hoveredMonth === i ? 'bg-brand-hover' : 'bg-[#c9d6f2]'"
                  :style="{ height: m.bytes ? `${Math.max(3, (m.bytes / monthMax) * 100)}%` : '2px' }"
                />
              </div>
            </div>
          </div>
          <div class="mt-2 flex gap-3 border-t border-line pt-2 sm:gap-5" aria-hidden="true">
            <span v-for="(m, i) in monthly" :key="m.month" class="flex-1 text-center text-[12px]"
                  :class="i === monthly.length - 1 ? 'font-medium text-ink' : 'text-ink-muted'">
              {{ monthName(m.month) }}
            </span>
          </div>
        </section>

        <!-- ============ Who uses the most ============ -->
        <section :class="CARD" aria-labelledby="top-title">
          <h2 id="top-title" class="text-lg">Biggest accounts</h2>
          <p class="mt-0.5 text-[12px] text-ink-muted">Uploaded files, as counted against their quota</p>
          <ol v-if="topAccounts.length" class="mt-5 flex flex-col gap-4">
            <li v-for="(a, i) in topAccounts" :key="a.id">
              <div class="flex items-baseline justify-between gap-3 text-sm">
                <span class="flex min-w-0 items-baseline gap-2">
                  <span class="w-3 shrink-0 text-[12px] text-ink-subtle tabular-nums">{{ i + 1 }}</span>
                  <span class="truncate text-ink">{{ a.name }}</span>
                </span>
                <span class="shrink-0 text-ink-muted tabular-nums">{{ bytes(a.bytes) }}</span>
              </div>
              <div class="mt-1.5 ml-5 h-1.5 overflow-hidden rounded-full bg-raised" aria-hidden="true">
                <div class="h-full rounded-full bg-brand" :style="{ width: `${(a.bytes / topMax) * 100}%` }" />
              </div>
            </li>
          </ol>
          <p v-else class="mt-5 text-sm text-ink-muted">Nobody has uploaded anything yet.</p>
        </section>
      </div>
    </template>
  </div>
</template>
