<script setup lang="ts">
/**
 * Every account, what each is allowed, how much it is using, and who is in it.
 * Two actions — make an account, change its limits — and which of them a row offers depends
 * on the kind of account you are signed in as (useStaffRights): the owner reaches admin and
 * client accounts, a technician reaches clients only. The server refuses the rest regardless;
 * what is hidden here is hidden to keep the page honest, not to keep anyone out.
 *
 * A blank limit field means "no limit". Storage is typed in GB here and sent as bytes, since
 * nobody thinks in bytes.
 */
import { computed, ref, watch } from 'vue'
import IconAdd from '~icons/material-symbols/add'
import IconSearch from '~icons/material-symbols/search'
import IconTune from '~icons/material-symbols/tune'

import { useAdminAccounts } from '@/hooks/useAdminAccounts'
import { useFormat } from '@/hooks/useFormat'
import { useStaffRights } from '@/hooks/useStaffRights'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppInput from '@/reusables/AppInput.vue'
import AppModal from '@/reusables/AppModal.vue'
import AppSelect from '@/reusables/AppSelect.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import OverflowMenu from '@/reusables/OverflowMenu.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import SkeletonBlock from '@/reusables/SkeletonBlock.vue'
import type { AccountKind, AdminAccountRead, AdminAccountUserRead } from '@/types/api'

const { accounts, isLoading, isSaving, error, formError, create, setLimits } = useAdminAccounts()
const { bytes, date } = useFormat()
const { issuable, maySetLimits, label: kindLabel, defaultLimits } = useStaffRights()

const GB = 1024 ** 3

const query = ref('')
/** Matches the account's name, its kind, or any of its people — the owner or a sub account. */
const rows = computed(() => {
  const q = query.value.trim().toLowerCase()
  return accounts.value.filter(
    (a) =>
      !q ||
      [a.name, kindLabel(a.kind), ...a.users.flatMap((u) => [u.username, u.display_name])].some((v) =>
        v.toLowerCase().includes(q),
      ),
  )
})

// --- Marks: what kind of account this is, and who is in it ---

const BADGE = 'inline-flex items-center rounded-full px-2 py-0.5 text-[11px] leading-4 whitespace-nowrap ring-1 ring-inset'
const TONES = {
  green: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  brand: 'bg-brand-soft text-brand ring-brand/20',
  muted: 'bg-surface text-ink-muted ring-line',
  ink: 'bg-ink text-ink-inverse ring-ink',
} as const

/** Only the accounts that are *not* ordinary customers carry a badge. A mark on every row
 *  marks nothing; a mark on the two that can sign in here is worth reading. This is the only
 *  badge on the page allowed to say "Owner", and it means the account kind — Paskall itself. */
const KIND_TONE: Partial<Record<AccountKind, keyof typeof TONES>> = { owner: 'ink', admin: 'brand' }

/** "Main user", not "Owner", even though the role is called `owner` in the data. This page
 *  already uses Owner for a *kind of account* — Paskall's own — and one word for two ideas made
 *  "Fortu Digital [Admin]" sit directly above "Fortu Digital @fortu [Owner]", which reads like a
 *  contradiction. Main user pairs with Sub account, which is the distinction this badge is
 *  actually drawing. The CMS keeps saying Owner to customers, where there is no kind to clash
 *  with. */
function badges(u: AdminAccountUserRead): { label: string; tone: keyof typeof TONES }[] {
  const out: { label: string; tone: keyof typeof TONES }[] = [
    u.role === 'owner' ? { label: 'Main user', tone: 'green' } : { label: 'Sub account', tone: 'brand' },
  ]
  if (!u.is_active) out.push({ label: 'Deactivated', tone: 'muted' })
  return out
}

// --- Limits as the form holds them: blank = no limit ---

/** Takes a string *or* a number: Vue casts v-model on a type="number" input to a number the
 *  moment it can be parsed, and back to '' when cleared — so the field is both, by turns. */
function toLimit(value: string | number): number | null {
  const t = String(value).trim()
  if (!t) return null
  const n = Number(t)
  return Number.isFinite(n) && n >= 0 ? Math.floor(n) : null
}
function gbToBytes(value: string | number): number | null {
  const gb = toLimit(value)
  return gb === null ? null : gb * GB
}
function bytesToGbText(value: number | null): string {
  return value === null ? '' : String(Math.round(value / GB))
}

// --- Create ---

const adding = ref(false)
/** Client unless this person cannot issue one — the common case first, either way. */
const blank = () => {
  const kind: AccountKind = issuable.value.includes('client') ? 'client' : (issuable.value[0] ?? 'client')
  return { kind, name: '', username: '', display_name: '', password: '', ...defaultLimits(kind) }
}
const form = ref(blank())

/** The dropdown only earns its place when there is a choice: a technician issues clients and
 *  nothing else, so they get a line of text instead. */
const kindOptions = computed(() => issuable.value.map((k) => ({ value: k, label: kindLabel(k) })))

/** Picking a type fills in what that type normally gets — 15 screens and 5 GB for an admin,
 *  no limit for a client. Typed over freely; this is a starting point, not a rule. */
watch(
  () => form.value.kind,
  (kind) => Object.assign(form.value, defaultLimits(kind)),
)

async function onCreate() {
  const ok = await create({
    kind: form.value.kind,
    name: form.value.name,
    username: form.value.username,
    display_name: form.value.display_name,
    password: form.value.password,
    max_screens: toLimit(form.value.screens),
    storage_quota_bytes: gbToBytes(form.value.storageGb),
  })
  if (ok) {
    adding.value = false
    form.value = blank()
  }
}

function openCreate() {
  form.value = blank()
  adding.value = true
}

// --- Edit limits ---

const editing = ref<AdminAccountRead | null>(null)
const limits = ref({ screens: '', storageGb: '' })

function openLimits(a: AdminAccountRead) {
  limits.value = {
    screens: a.max_screens === null ? '' : String(a.max_screens),
    storageGb: bytesToGbText(a.storage_quota_bytes),
  }
  editing.value = a
}

async function saveLimits() {
  if (!editing.value) return
  // Both sent every time: a blank field is an explicit "no limit", not "leave it alone".
  const ok = await setLimits(editing.value.id, {
    max_screens: toLimit(limits.value.screens),
    storage_quota_bytes: gbToBytes(limits.value.storageGb),
  })
  if (ok) editing.value = null
}

// --- Display ---

// Desktop columns already say "Screens" / "Storage", so the cell stays terse.
function screensText(a: AdminAccountRead): string {
  return a.max_screens === null ? `${a.screens_used} · no limit` : `${a.screens_used} of ${a.max_screens}`
}
function storageText(a: AdminAccountRead): string {
  const used = bytes(a.storage_used_bytes)
  return a.storage_quota_bytes === null ? `${used} · no limit` : `${used} of ${bytes(a.storage_quota_bytes)}`
}
// Phones have no column headers, so each figure names itself: "10 of 5 screens", "2 screens, no limit".
function screensTextMobile(a: AdminAccountRead): string {
  const n = a.screens_used
  const unit = `screen${n === 1 ? '' : 's'}`
  return a.max_screens === null ? `${n} ${unit}, no limit` : `${n} of ${a.max_screens} ${unit}`
}
function storageTextMobile(a: AdminAccountRead): string {
  const used = bytes(a.storage_used_bytes)
  return a.storage_quota_bytes === null ? `${used} storage, no limit` : `${used} of ${bytes(a.storage_quota_bytes)}`
}
function atScreenLimit(a: AdminAccountRead): boolean {
  return a.max_screens !== null && a.screens_used >= a.max_screens
}
function atStorageLimit(a: AdminAccountRead): boolean {
  return a.storage_quota_bytes !== null && a.storage_used_bytes >= a.storage_quota_bytes
}

const MENU_ITEM = 'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm hover:bg-surface'
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle title="Accounts" subtitle="Every account, what each is allowed, and how much it is using.">
      <template #actions>
        <AppButton v-if="issuable.length" size="sm" @click="openCreate">
          <IconAdd class="size-4" aria-hidden="true" />
          New account
        </AppButton>
      </template>
    </PageTitle>

    <label class="relative block w-full sm:w-72">
      <IconSearch class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-subtle" />
      <input
        v-model="query"
        type="search"
        placeholder="Search by account, type or person"
        aria-label="Search accounts and their people"
        class="h-9 w-full rounded-lg border border-line-strong bg-canvas pr-3 pl-9 text-sm text-ink
               placeholder:text-ink-subtle focus:border-ink focus:outline-none"
      />
    </label>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>

    <!-- No horizontal scroll container: it would clip the ⋮ menus. Columns drop out on
         narrow screens instead. -->
    <div class="rounded-2xl bg-canvas">
      <table class="w-full table-fixed text-left text-sm">
        <thead class="text-[12px] text-ink-muted">
          <tr class="bg-surface">
            <th class="rounded-tl-2xl px-4 py-3 font-normal">Account</th>
            <th class="hidden w-36 px-4 py-3 font-normal sm:table-cell">Screens</th>
            <th class="hidden w-44 px-4 py-3 font-normal sm:table-cell">Storage</th>
            <th class="hidden w-32 px-4 py-3 font-normal md:table-cell">Created</th>
            <th class="w-14 rounded-tr-2xl px-2 py-3"><span class="sr-only">Actions</span></th>
          </tr>
        </thead>

        <tbody v-if="isLoading && !accounts.length" class="divide-y divide-line" aria-busy="true">
          <tr v-for="i in 3" :key="i">
            <td class="px-4 py-3.5">
              <SkeletonBlock class="h-3.5 w-40 max-w-full rounded-md" />
              <SkeletonBlock class="mt-1.5 h-3 w-24 max-w-full rounded-md" />
            </td>
            <td class="hidden px-4 py-3.5 sm:table-cell"><SkeletonBlock class="h-3 w-16 rounded-md" /></td>
            <td class="hidden px-4 py-3.5 sm:table-cell"><SkeletonBlock class="h-3 w-24 rounded-md" /></td>
            <td class="hidden px-4 py-3.5 md:table-cell"><SkeletonBlock class="h-3 w-20 rounded-md" /></td>
            <td />
          </tr>
        </tbody>

        <tbody v-else class="divide-y divide-line">
          <tr v-for="a in rows" :key="a.id">
            <td class="px-4 py-3">
              <p class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                <span class="truncate font-medium text-ink">{{ a.name }}</span>
                <span v-if="KIND_TONE[a.kind]" :class="[BADGE, TONES[KIND_TONE[a.kind]!]]">
                  {{ kindLabel(a.kind) }}
                </span>
              </p>
              <p v-if="!a.users.length" class="text-[13px] text-danger">no users</p>
              <!-- The owner, then the sub accounts they made, tucked under them and marked. -->
              <ul v-else class="mt-1 flex flex-col gap-1 text-[13px]">
                <li
                  v-for="u in a.users"
                  :key="u.id"
                  class="flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-0.5"
                  :class="[u.role !== 'owner' && 'ml-2 border-l-2 border-line pl-2', !u.is_active && 'opacity-60']"
                >
                  <span class="truncate text-ink">{{ u.display_name }}</span>
                  <span class="truncate text-ink-muted">@{{ u.username }}</span>
                  <span v-for="b in badges(u)" :key="b.label" :class="[BADGE, TONES[b.tone]]">{{ b.label }}</span>
                </li>
              </ul>
              <!-- Phones: no Screens/Storage columns, so the figures go here. -->
              <p class="mt-1 text-[13px] text-ink-muted sm:hidden">
                <span :class="atScreenLimit(a) && 'text-danger'">{{ screensTextMobile(a) }}</span>
                ·
                <span :class="atStorageLimit(a) && 'text-danger'">{{ storageTextMobile(a) }}</span>
              </p>
            </td>
            <td class="hidden px-4 py-3 whitespace-nowrap tabular-nums sm:table-cell"
                :class="atScreenLimit(a) ? 'text-danger' : 'text-ink'">
              {{ screensText(a) }}
            </td>
            <td class="hidden px-4 py-3 whitespace-nowrap tabular-nums sm:table-cell"
                :class="atStorageLimit(a) ? 'text-danger' : 'text-ink'">
              {{ storageText(a) }}
            </td>
            <td class="hidden px-4 py-3 whitespace-nowrap text-ink-muted md:table-cell">{{ date(a.created_at) }}</td>
            <td class="px-2 py-3">
              <!-- No menu at all on an account this person may not act on, rather than a menu
                   whose only item answers 403. -->
              <OverflowMenu
                v-if="maySetLimits(a)"
                v-slot="{ close }"
                class="ml-auto w-fit"
                :label="`Actions for ${a.name}`"
              >
                <button type="button" role="menuitem" :class="[MENU_ITEM, 'text-ink']" @click="close(); openLimits(a)">
                  <IconTune class="size-4 shrink-0 text-ink-muted" aria-hidden="true" />Edit limits
                </button>
              </OverflowMenu>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="5" class="px-4 py-10 text-center text-ink-muted">
              {{ query ? 'No accounts match your search.' : 'No accounts yet.' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create -->
    <AppModal v-if="adding" title="New account" @close="adding = false">
      <form class="flex flex-col gap-3" @submit.prevent="onCreate">
        <div v-if="kindOptions.length > 1" class="flex flex-col gap-1.5">
          <label for="a-kind" class="text-[13px] text-ink-muted">Account type</label>
          <AppSelect id="a-kind" v-model="form.kind" :options="kindOptions" />
          <p class="text-[13px] text-ink-subtle">
            {{ form.kind === 'admin'
              ? 'A technician: uses the CMS and this monitoring app, and can issue client accounts.'
              : 'A customer: the CMS only.' }}
          </p>
        </div>
        <p v-else class="text-[13px] text-ink-subtle">
          A client account: a customer, with access to the CMS only.
        </p>

        <AppInput id="a-name" v-model="form.name" label="Account name" required placeholder="Kopi Kenangan Jakarta" />
        <p class="pt-1 text-[12px] font-medium tracking-wider text-ink-subtle uppercase">Main user</p>
        <AppInput id="a-username" v-model="form.username" label="Username" required
                  hint="They sign in with this. Letters, digits, dot, underscore, hyphen." />
        <AppInput id="a-display" v-model="form.display_name" label="Name" required />
        <AppInput id="a-password" v-model="form.password" label="Password" type="password" required
                  hint="At least 8 characters. You pass this on to them yourself — there is no email." />
        <p class="pt-1 text-[12px] font-medium tracking-wider text-ink-subtle uppercase">Limits</p>
        <div class="grid grid-cols-2 gap-3">
          <AppInput id="a-screens" v-model="form.screens" label="Screens" type="number" min="0" step="1"
                    hint="Blank = no limit" />
          <AppInput id="a-storage" v-model="form.storageGb" label="Storage (GB)" type="number" min="0" step="1"
                    hint="Blank = no limit" />
        </div>
        <ModalActions>
          <AppButton variant="secondary" size="sm" type="button" @click="adding = false">Cancel</AppButton>
          <AppButton size="sm" type="submit" :loading="isSaving" :disabled="form.password.length < 8">Create</AppButton>
        </ModalActions>
      </form>
    </AppModal>

    <!-- Edit limits -->
    <AppModal v-if="editing" :title="`Limits for ${editing.name}`" @close="editing = null">
      <form class="flex flex-col gap-3" @submit.prevent="saveLimits">
        <p class="text-[13px] text-ink-muted">
          Using {{ editing.screens_used }} screen{{ editing.screens_used === 1 ? '' : 's' }} and
          {{ bytes(editing.storage_used_bytes) }} right now.
        </p>
        <div class="grid grid-cols-2 gap-3">
          <AppInput id="l-screens" v-model="limits.screens" label="Screens" type="number" min="0" step="1"
                    hint="Blank = no limit" />
          <AppInput id="l-storage" v-model="limits.storageGb" label="Storage (GB)" type="number" min="0" step="1"
                    hint="Blank = no limit" />
        </div>
        <ModalActions>
          <AppButton variant="secondary" size="sm" type="button" @click="editing = null">Cancel</AppButton>
          <AppButton size="sm" type="submit" :loading="isSaving">Save</AppButton>
        </ModalActions>
      </form>
    </AppModal>
  </div>
</template>
