<script setup lang="ts">
/**
 * One account, in full: what it may use and how much of that it is using, when it ends, and
 * everyone who can sign in to it. Shown in the side panel the Accounts table opens, so the list
 * stays in view behind it.
 *
 * The two actions are the table's own (Edit limits, Reset password); this only asks for them,
 * and the page opens the same dialogs either way.
 */
import { computed } from 'vue'
import IconGroup from '~icons/material-symbols/group-outline'
import IconKey from '~icons/material-symbols/key-outline'
import IconStorage from '~icons/material-symbols/cloud-outline'
import IconTune from '~icons/material-symbols/tune'
import IconTv from '~icons/material-symbols/tv-outline'

import { BADGE, KIND_TONE, TONES, initials, mainUser, otherUsers, useAccountMarks } from '@/hooks/useAccountMarks'
import { useExpiry } from '@/hooks/useExpiry'
import { useFormat } from '@/hooks/useFormat'
import { useStaffRights } from '@/hooks/useStaffRights'
import AppButton from '@/reusables/AppButton.vue'
import type { AdminAccountRead } from '@/types/api'

const props = defineProps<{ account: AdminAccountRead; canAct: boolean }>()
const emit = defineEmits<{ editLimits: []; resetPassword: [] }>()

const { bytes, date } = useFormat()
const { lastDayText } = useExpiry()
const { label: kindLabel } = useStaffRights()
const { endBadge, userBadges } = useAccountMarks()

const main = computed(() => mainUser(props.account))
const subs = computed(() => otherUsers(props.account))
const end = computed(() => endBadge(props.account))

/** A share of a limit, for the little bars. Null when there is no limit to be a share of. */
function share(used: number, limit: number | null): number | null {
  if (limit === null) return null
  return limit === 0 ? 100 : Math.min(100, (used / limit) * 100)
}

const stats = computed(() => {
  const a = props.account
  return [
    {
      key: 'screens',
      icon: IconTv,
      label: 'Screens',
      value: String(a.screens_used),
      of: a.max_screens === null ? 'no limit' : `of ${a.max_screens}`,
      share: share(a.screens_used, a.max_screens),
    },
    {
      key: 'storage',
      icon: IconStorage,
      label: 'Storage',
      value: bytes(a.storage_used_bytes),
      of: a.storage_quota_bytes === null ? 'no limit' : `of ${bytes(a.storage_quota_bytes)}`,
      share: share(a.storage_used_bytes, a.storage_quota_bytes),
    },
    {
      key: 'subs',
      icon: IconGroup,
      label: 'Sub accounts',
      value: String(subs.value.length),
      of: subs.value.length === 1 ? 'person' : 'people',
      share: null,
    },
  ]
})

const LABEL = 'text-[11px] font-medium tracking-wider text-ink-subtle uppercase'
</script>

<template>
  <div class="flex flex-col">
    <!-- Who -->
    <header class="border-b border-line px-5 pt-6 pb-5 pr-14 sm:px-6">
      <div class="flex items-center gap-3.5">
        <span
          class="grid size-12 shrink-0 place-items-center rounded-full bg-linear-to-br from-brand-strong to-brand-bright
                 font-display text-lg font-medium text-white"
          aria-hidden="true"
        >
          {{ initials(account.name) }}
        </span>
        <div class="min-w-0">
          <p class="text-[11px] font-medium tracking-wider text-ink-subtle uppercase">Organization</p>
          <h2 class="text-xl [overflow-wrap:anywhere]">{{ account.name }}</h2>
          <p v-if="main" class="truncate text-[13px] text-ink-muted">
            {{ main.display_name }} · @{{ main.username }}
          </p>
          <p v-else class="text-[13px] text-danger">No main user</p>
        </div>
      </div>
      <p class="mt-3 flex flex-wrap gap-1.5">
        <span :class="[BADGE, TONES[KIND_TONE[account.kind] ?? 'muted']]">{{ kindLabel(account.kind) }}</span>
        <span v-if="end" :class="[BADGE, TONES[end.tone]]">{{ end.label }}</span>
        <span v-if="main && !main.is_active" :class="[BADGE, TONES.muted]">Deactivated</span>
      </p>
      <div v-if="canAct" class="mt-4 flex flex-wrap gap-2">
        <AppButton variant="secondary" size="sm" @click="emit('editLimits')">
          <IconTune class="size-4" aria-hidden="true" />Edit limits
        </AppButton>
        <AppButton variant="secondary" size="sm" @click="emit('resetPassword')">
          <IconKey class="size-4" aria-hidden="true" />Reset password
        </AppButton>
      </div>
    </header>

    <div class="flex flex-col gap-6 px-5 py-5 sm:px-6">
      <!-- What it uses -->
      <section aria-label="Usage" class="grid grid-cols-3 gap-2">
        <div v-for="s in stats" :key="s.key" class="rounded-xl bg-surface p-3">
          <p class="flex items-start gap-1.5 text-[11px] leading-tight text-ink-muted">
            <component :is="s.icon" class="size-3.5 shrink-0" aria-hidden="true" />
            <span>{{ s.label }}</span>
          </p>
          <p class="mt-1.5 font-display text-xl leading-tight text-ink tabular-nums"
             :class="s.share !== null && s.share >= 100 && '!text-danger'">
            {{ s.value }}
          </p>
          <p class="truncate text-[11px] text-ink-muted">{{ s.of }}</p>
          <div v-if="s.share !== null" class="mt-2 h-1 overflow-hidden rounded-full bg-line" aria-hidden="true">
            <div class="h-full rounded-full" :class="s.share >= 100 ? 'bg-danger' : 'bg-brand'"
                 :style="{ width: `${Math.max(s.share, 2)}%` }" />
          </div>
        </div>
      </section>

      <!-- Details -->
      <section aria-labelledby="details-title">
        <h3 id="details-title" :class="LABEL">Details</h3>
        <dl class="mt-3 grid grid-cols-2 gap-x-4 gap-y-3.5 text-sm">
          <div>
            <dt class="text-[12px] text-ink-muted">Account type</dt>
            <dd class="text-ink">{{ kindLabel(account.kind) }}</dd>
          </div>
          <div>
            <dt class="text-[12px] text-ink-muted">Created</dt>
            <dd class="text-ink">{{ date(account.created_at) }}</dd>
          </div>
          <div>
            <dt class="text-[12px] text-ink-muted">{{ account.is_expired ? 'Ended' : 'Active until' }}</dt>
            <dd :class="account.is_expired ? 'text-danger' : account.expires_at ? 'text-ink' : 'text-ink-muted'">
              {{ account.expires_at ? lastDayText(account.expires_at) : 'No end date' }}
            </dd>
          </div>
          <div>
            <dt class="text-[12px] text-ink-muted">Signs in with</dt>
            <dd class="truncate text-ink">{{ main ? `@${main.username}` : '—' }}</dd>
          </div>
          <div v-if="main?.must_change_password" class="col-span-2">
            <dt class="text-[12px] text-ink-muted">Password</dt>
            <dd class="text-ink">Temporary — they haven't signed in yet to choose their own</dd>
          </div>
        </dl>
      </section>

      <!-- People -->
      <section aria-labelledby="people-title">
        <h3 id="people-title" :class="LABEL">People · {{ account.users.length }}</h3>
        <ul class="mt-3 divide-y divide-line rounded-xl ring-1 ring-line">
          <li
            v-for="u in [...(main ? [main] : []), ...subs]"
            :key="u.id"
            class="flex items-start gap-3 px-3.5 py-3"
            :class="!u.is_active && 'opacity-60'"
          >
            <span
              class="grid size-8 shrink-0 place-items-center rounded-full text-[12px] font-medium"
              :class="u.role === 'owner' ? 'bg-brand text-white' : 'bg-brand-soft text-brand'"
              aria-hidden="true"
            >
              {{ initials(u.display_name || u.username) }}
            </span>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm text-ink">{{ u.display_name }}</p>
              <p class="truncate text-[12px] text-ink-muted">@{{ u.username }} · joined {{ date(u.created_at) }}</p>
              <p class="mt-1.5 flex flex-wrap gap-1">
                <span v-for="b in userBadges(u)" :key="b.label" :class="[BADGE, TONES[b.tone]]">{{ b.label }}</span>
              </p>
            </div>
          </li>
          <li v-if="!account.users.length" class="px-3.5 py-3 text-sm text-danger">Nobody can sign in to this account.</li>
        </ul>
        <p v-if="!subs.length && main" class="mt-2 text-[12px] text-ink-subtle">
          No sub accounts yet. The main user adds them from the CMS.
        </p>
      </section>
    </div>
  </div>
</template>
