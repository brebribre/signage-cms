<script setup lang="ts">
/**
 * Every account, what each is allowed and how much it is using. One line per account — its sub
 * accounts are a count here, and listed by name in the side panel a click on the row opens
 * (AccountDetailsContainer), so a busy account doesn't push the rest of the list down.
 * Two actions — make an account, change its limits — and which of them a row offers depends
 * on the kind of account you are signed in as (useStaffRights): the owner reaches admin and
 * client accounts, a technician reaches clients only. The server refuses the rest regardless;
 * what is hidden here is hidden to keep the page honest, not to keep anyone out.
 *
 * A blank limit field means "no limit". Storage is typed in GB here and sent as bytes, since
 * nobody thinks in bytes. The end date ("Active until") is a limit too, set in the same places:
 * blank means the account never ends. Past it, the account is read-only in the CMS, and an
 * admin account loses this app (see ACCOUNTS.md).
 */
import { computed, ref, watch } from 'vue'
import IconAdd from '~icons/material-symbols/add'
import IconSearch from '~icons/material-symbols/search'
import IconTune from '~icons/material-symbols/tune'
import IconKey from '~icons/material-symbols/key-outline'
import IconGroup from '~icons/material-symbols/group-outline'

import { BADGE, KIND_TONE, TONES, initials, mainUser, otherUsers, useAccountMarks } from '@/hooks/useAccountMarks'
import { useAdminAccounts } from '@/hooks/useAdminAccounts'
import { useExpiry } from '@/hooks/useExpiry'
import { useFormat } from '@/hooks/useFormat'
import { useStaffRights } from '@/hooks/useStaffRights'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppDrawer from '@/reusables/AppDrawer.vue'
import AppInput from '@/reusables/AppInput.vue'
import AppModal from '@/reusables/AppModal.vue'
import AppSelect from '@/reusables/AppSelect.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import OverflowMenu from '@/reusables/OverflowMenu.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import SkeletonBlock from '@/reusables/SkeletonBlock.vue'
import type { AccountKind, AdminAccountRead } from '@/types/api'

import AccountDetailsContainer from './AccountDetailsContainer.vue'

const { accounts, isLoading, isSaving, error, formError, create, setLimits, resetPassword } = useAdminAccounts()
const { bytes } = useFormat()
const { issuable, maySetLimits, label: kindLabel, defaultLimits } = useStaffRights()
const { toExpiresAt, toDayField, lastDayText } = useExpiry()
const { endBadge } = useAccountMarks()

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

// --- The side panel: one account in full, opened by clicking its row ---

/** By id, not the row itself: after a save the list is fetched again, and the panel should show
 *  the fresh account, not the one it was opened with. */
const selectedId = ref<string | null>(null)
const selected = computed(() => accounts.value.find((a) => a.id === selectedId.value) ?? null)

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
  return { kind, name: '', username: '', display_name: '', password: '', activeUntil: '', ...defaultLimits(kind) }
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
    expires_at: toExpiresAt(form.value.activeUntil),
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
const limits = ref({ screens: '', storageGb: '', activeUntil: '' })

function openLimits(a: AdminAccountRead) {
  limits.value = {
    screens: a.max_screens === null ? '' : String(a.max_screens),
    storageGb: bytesToGbText(a.storage_quota_bytes),
    activeUntil: toDayField(a.expires_at),
  }
  editing.value = a
}

async function saveLimits() {
  if (!editing.value) return
  // Both sent every time: a blank field is an explicit "no limit", not "leave it alone".
  const ok = await setLimits(editing.value.id, {
    max_screens: toLimit(limits.value.screens),
    storage_quota_bytes: gbToBytes(limits.value.storageGb),
    expires_at: toExpiresAt(limits.value.activeUntil),
  })
  if (ok) editing.value = null
}

// --- Reset password: a temporary one for the main user, who picks their own at next sign-in ---

const resetting = ref<AdminAccountRead | null>(null)
const tempPassword = ref('')
const resetDone = ref<string | null>(null)

/** Twelve characters with no look-alikes (no 0/O, 1/l/I), easy to read out or type from a
 *  message. From the browser's cryptographic generator, not Math.random. */
function generatePassword(): string {
  const alphabet = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  const bytes = crypto.getRandomValues(new Uint32Array(12))
  return Array.from(bytes, (b) => alphabet[b % alphabet.length]).join('')
}

function openReset(a: AdminAccountRead) {
  tempPassword.value = generatePassword()
  resetDone.value = null
  resetting.value = a
}

async function saveReset() {
  if (!resetting.value) return
  const who = mainUser(resetting.value)
  if (await resetPassword(resetting.value.id, tempPassword.value)) {
    resetDone.value = who ? `@${who.username}` : resetting.value.name
  }
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
function endText(a: AdminAccountRead): string {
  return a.expires_at ? lastDayText(a.expires_at) : 'No end date'
}
/** What the date picked in a form will do, said before anyone presses Save. */
function endHint(day: string): string {
  if (!day) return 'Blank = no end date.'
  const at = toExpiresAt(day)!
  return new Date(at).getTime() <= Date.now()
    ? 'That day has passed: the account turns read-only as soon as you save.'
    : 'After this day the account turns read-only. Its screens keep playing.'
}
/** How much of a limit is used, for the thin bar under a figure. Null when there is no limit. */
function share(used: number, limit: number | null): number | null {
  if (limit === null) return null
  return limit === 0 ? 100 : Math.min(100, (used / limit) * 100)
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
        placeholder="Search by organization, type or person"
        aria-label="Search organizations and their people"
        class="h-9 w-full rounded-lg border border-line-strong bg-canvas pr-3 pl-9 text-sm text-ink
               placeholder:text-ink-subtle focus:border-ink focus:outline-none"
      />
    </label>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>

    <!-- One line per account. A click anywhere on the line opens the account in the side panel;
         the name is also a real button, so the keyboard gets there too. No horizontal scroll
         container: it would clip the ⋮ menus. Columns drop out on narrow screens instead, and
         what they held stacks under the name. -->
    <div class="overflow-hidden rounded-2xl bg-canvas">
      <table class="w-full table-fixed text-left text-sm">
        <thead class="text-[12px] text-ink-muted">
          <tr class="bg-surface">
            <th class="px-4 py-3 font-normal">Organization</th>
            <th class="hidden w-28 px-4 py-3 font-normal md:table-cell">Sub accounts</th>
            <th class="hidden w-32 px-4 py-3 font-normal sm:table-cell">Screens</th>
            <th class="hidden w-36 px-4 py-3 font-normal sm:table-cell lg:w-40">Storage</th>
            <th class="hidden w-28 px-4 py-3 font-normal lg:table-cell">Active until</th>
            <th class="w-12 px-2 py-3"><span class="sr-only">Actions</span></th>
          </tr>
        </thead>

        <tbody v-if="isLoading && !accounts.length" class="divide-y divide-line" aria-busy="true">
          <tr v-for="i in 4" :key="i">
            <td class="px-4 py-3.5">
              <span class="flex items-center gap-3">
                <SkeletonBlock class="size-9 shrink-0 rounded-full" />
                <span class="flex flex-col gap-1.5"><SkeletonBlock class="h-3.5 w-40 max-w-full rounded-md" /><SkeletonBlock class="h-3 w-24 rounded-md" /></span>
              </span>
            </td>
            <td class="hidden px-4 py-3.5 md:table-cell"><SkeletonBlock class="h-3 w-8 rounded-md" /></td>
            <td class="hidden px-4 py-3.5 sm:table-cell"><SkeletonBlock class="h-3 w-16 rounded-md" /></td>
            <td class="hidden px-4 py-3.5 sm:table-cell"><SkeletonBlock class="h-3 w-24 rounded-md" /></td>
            <td class="hidden px-4 py-3.5 lg:table-cell"><SkeletonBlock class="h-3 w-20 rounded-md" /></td>
            <td />
          </tr>
        </tbody>

        <tbody v-else class="divide-y divide-line border-t border-line">
          <tr
            v-for="a in rows"
            :key="a.id"
            class="cursor-pointer transition-colors duration-150"
            :class="[
              selectedId === a.id ? 'bg-brand-soft' : 'hover:bg-surface',
              mainUser(a) && !mainUser(a)!.is_active && 'opacity-60',
            ]"
            @click="selectedId = a.id"
          >
            <td class="px-4 py-3">
              <div class="flex min-w-0 items-start gap-3">
                <span
                  class="mt-0.5 grid size-9 shrink-0 place-items-center rounded-full font-display text-[13px] font-medium"
                  :class="a.kind === 'client' ? 'bg-brand-soft text-brand' : 'bg-linear-to-br from-brand-strong to-brand-bright text-white'"
                  aria-hidden="true"
                >
                  {{ initials(a.name) }}
                </span>
                <div class="min-w-0 flex-1">
                  <p class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                    <button
                      type="button"
                      class="truncate text-left font-medium text-ink focus-visible:rounded-sm focus-visible:outline-2
                             focus-visible:outline-offset-2 focus-visible:outline-brand-bright"
                      @click.stop="selectedId = a.id"
                    >
                      {{ a.name }}
                    </button>
                    <span v-if="KIND_TONE[a.kind]" :class="[BADGE, TONES[KIND_TONE[a.kind]!]]">{{ kindLabel(a.kind) }}</span>
                    <span v-if="mainUser(a) && !mainUser(a)!.is_active" :class="[BADGE, TONES.muted]">Deactivated</span>
                    <span v-if="mainUser(a)?.must_change_password" :class="[BADGE, TONES.muted]"
                          title="They haven't signed in yet to choose their own password">
                      Temporary password
                    </span>
                    <span v-if="endBadge(a)" :class="[BADGE, TONES[endBadge(a)!.tone]]">{{ endBadge(a)!.label }}</span>
                  </p>
                  <p v-if="mainUser(a)" class="truncate text-[13px] text-ink-muted">
                    {{ mainUser(a)!.display_name }} · @{{ mainUser(a)!.username }}
                  </p>
                  <p v-else class="text-[13px] text-danger">no users</p>

                  <!-- Narrow screens: the columns that dropped out, as lines that name themselves. -->
                  <p v-if="otherUsers(a).length" class="text-[13px] text-ink-muted md:hidden">
                    {{ otherUsers(a).length }} sub account{{ otherUsers(a).length === 1 ? '' : 's' }}
                  </p>
                  <p v-if="a.expires_at" class="text-[13px] text-ink-muted lg:hidden" :class="a.is_expired && '!text-danger'">
                    {{ a.is_expired ? 'Ended' : 'Active until' }} {{ lastDayText(a.expires_at) }}
                  </p>
                  <p class="text-[13px] text-ink-muted sm:hidden">
                    <span :class="atScreenLimit(a) && 'text-danger'">{{ screensTextMobile(a) }}</span>
                    ·
                    <span :class="atStorageLimit(a) && 'text-danger'">{{ storageTextMobile(a) }}</span>
                  </p>
                </div>
              </div>
            </td>

            <td class="hidden px-4 py-3 md:table-cell">
              <span v-if="otherUsers(a).length" class="inline-flex items-center gap-1.5 text-ink tabular-nums">
                <IconGroup class="size-4 text-ink-subtle" aria-hidden="true" />{{ otherUsers(a).length }}
              </span>
              <span v-else class="text-ink-subtle">None</span>
            </td>
            <td class="hidden px-4 py-3 sm:table-cell">
              <p class="whitespace-nowrap tabular-nums" :class="atScreenLimit(a) ? 'text-danger' : 'text-ink'">{{ screensText(a) }}</p>
              <div v-if="share(a.screens_used, a.max_screens) !== null" class="mt-1.5 h-1 w-24 overflow-hidden rounded-full bg-raised" aria-hidden="true">
                <div class="h-full rounded-full" :class="atScreenLimit(a) ? 'bg-danger' : 'bg-brand'"
                     :style="{ width: `${Math.max(share(a.screens_used, a.max_screens)!, 3)}%` }" />
              </div>
            </td>
            <td class="hidden px-4 py-3 sm:table-cell">
              <p class="whitespace-nowrap tabular-nums" :class="atStorageLimit(a) ? 'text-danger' : 'text-ink'">{{ storageText(a) }}</p>
              <div v-if="share(a.storage_used_bytes, a.storage_quota_bytes) !== null" class="mt-1.5 h-1 w-28 overflow-hidden rounded-full bg-raised" aria-hidden="true">
                <div class="h-full rounded-full" :class="atStorageLimit(a) ? 'bg-danger' : 'bg-brand'"
                     :style="{ width: `${Math.max(share(a.storage_used_bytes, a.storage_quota_bytes)!, 3)}%` }" />
              </div>
            </td>
            <td class="hidden px-4 py-3 whitespace-nowrap lg:table-cell"
                :class="a.is_expired ? 'text-danger' : a.expires_at ? 'text-ink' : 'text-ink-muted'">
              {{ endText(a) }}
            </td>
            <td class="px-2 py-3" @click.stop>
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
                <button type="button" role="menuitem" :class="[MENU_ITEM, 'text-ink']" @click="close(); openReset(a)">
                  <IconKey class="size-4 shrink-0 text-ink-muted" aria-hidden="true" />Reset password
                </button>
              </OverflowMenu>
            </td>
          </tr>

          <tr v-if="!rows.length">
            <td colspan="6" class="px-4 py-10 text-center text-ink-muted">
              {{ query ? 'No accounts match your search.' : 'No accounts yet.' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- One account in full. Held open while a dialog from it is up, so Escape closes the dialog
         first and leaves the panel where it was. -->
    <AppDrawer
      v-if="selected"
      :label="`Organization ${selected.name}`"
      :dismissible="!editing && !resetting && !adding"
      @close="selectedId = null"
    >
      <AccountDetailsContainer
        :account="selected"
        :can-act="maySetLimits(selected)"
        @edit-limits="openLimits(selected)"
        @reset-password="openReset(selected)"
      />
    </AppDrawer>

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

        <AppInput id="a-name" v-model="form.name" label="Organization" required placeholder="Kopi Kenangan Jakarta"
                  hint="The company or shop this account is for." />
        <p class="pt-1 text-[12px] font-medium tracking-wider text-ink-subtle uppercase">Main user</p>
        <AppInput id="a-username" v-model="form.username" label="Username" required
                  hint="They sign in with this. Letters, digits, dot, underscore, hyphen." />
        <AppInput id="a-display" v-model="form.display_name" label="Full name" required placeholder="Budi Santoso"
                  hint="The person who signs in, not the organization." />
        <AppInput id="a-password" v-model="form.password" label="Password" type="password" required
                  hint="Temporary: they choose their own when they first sign in, so you never know it. At least 8 characters." />
        <p class="pt-1 text-[12px] font-medium tracking-wider text-ink-subtle uppercase">Limits</p>
        <div class="grid grid-cols-2 gap-3">
          <AppInput id="a-screens" v-model="form.screens" label="Screens" type="number" min="0" step="1"
                    hint="Blank = no limit" />
          <AppInput id="a-storage" v-model="form.storageGb" label="Storage (GB)" type="number" min="0" step="1"
                    hint="Blank = no limit" />
        </div>
        <AppInput id="a-until" v-model="form.activeUntil" label="Active until" type="date"
                  :hint="endHint(form.activeUntil)" />
        <ModalActions>
          <AppButton variant="secondary" size="sm" type="button" @click="adding = false">Cancel</AppButton>
          <AppButton size="sm" type="submit" :loading="isSaving" :disabled="form.password.length < 8">Create</AppButton>
        </ModalActions>
      </form>
    </AppModal>

    <!-- Reset password -->
    <AppModal v-if="resetting" :title="`Reset password for ${resetting.name}`" @close="resetting = null">
      <div v-if="resetDone" class="flex flex-col gap-3">
        <p class="text-sm text-ink">
          Done. Give {{ resetDone }} this password:
        </p>
        <p class="rounded-lg bg-surface px-3 py-2 font-mono text-base tracking-wide text-ink select-all">{{ tempPassword }}</p>
        <p class="text-[13px] text-ink-muted">
          They'll choose their own as soon as they sign in. Their other sessions have been signed out.
        </p>
        <ModalActions>
          <AppButton size="sm" type="button" @click="resetting = null">Close</AppButton>
        </ModalActions>
      </div>
      <form v-else class="flex flex-col gap-3" @submit.prevent="saveReset">
        <p class="text-[13px] text-ink-muted">
          For someone who's forgotten theirs. This sets a temporary password for
          {{ mainUser(resetting) ? `@${mainUser(resetting)!.username}` : 'the main user' }}, and signs them out
          everywhere. They choose their own as soon as they sign in with it.
        </p>
        <div class="flex items-end gap-2">
          <div class="min-w-0 flex-1">
            <AppInput id="r-password" v-model="tempPassword" label="Temporary password" class="font-mono" required />
          </div>
          <AppButton variant="secondary" size="sm" type="button" class="mb-0.5" @click="tempPassword = generatePassword()">
            Generate
          </AppButton>
        </div>
        <ModalActions>
          <AppButton variant="secondary" size="sm" type="button" @click="resetting = null">Cancel</AppButton>
          <AppButton size="sm" type="submit" :loading="isSaving" :disabled="tempPassword.length < 8">Reset password</AppButton>
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
        <AppAlert v-if="editing.is_expired" tone="danger">
          This account has expired. It can sign in and look, but not change anything. Pick a new
          day, or remove the end date, to renew it.
        </AppAlert>
        <div class="grid grid-cols-2 gap-3">
          <AppInput id="l-screens" v-model="limits.screens" label="Screens" type="number" min="0" step="1"
                    hint="Blank = no limit" />
          <AppInput id="l-storage" v-model="limits.storageGb" label="Storage (GB)" type="number" min="0" step="1"
                    hint="Blank = no limit" />
        </div>
        <AppInput id="l-until" v-model="limits.activeUntil" label="Active until" type="date"
                  :hint="endHint(limits.activeUntil)" />
        <button v-if="limits.activeUntil" type="button" class="self-start text-[13px] text-brand hover:underline"
                @click="limits.activeUntil = ''">
          Remove end date
        </button>
        <ModalActions>
          <AppButton variant="secondary" size="sm" type="button" @click="editing = null">Cancel</AppButton>
          <AppButton size="sm" type="submit" :loading="isSaving">Save</AppButton>
        </ModalActions>
      </form>
    </AppModal>
  </div>
</template>
