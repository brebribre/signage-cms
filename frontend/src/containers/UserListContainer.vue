<script setup lang="ts">
import { computed, ref } from 'vue'
import IconAdd from '~icons/material-symbols/add'
import IconDeleteOutline from '~icons/material-symbols/delete-outline'
import IconKeyOutline from '~icons/material-symbols/key-outline'
import IconPersonCheckOutline from '~icons/material-symbols/person-check-outline'
import IconPersonOffOutline from '~icons/material-symbols/person-off-outline'
import IconSearch from '~icons/material-symbols/search'
import IconTvOutline from '~icons/material-symbols/tv-outline'

import { useAuth } from '@/hooks/useAuth'
import { useFormat } from '@/hooks/useFormat'
import { useUsers } from '@/hooks/useUsers'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppInput from '@/reusables/AppInput.vue'
import AppModal from '@/reusables/AppModal.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import OverflowMenu from '@/reusables/OverflowMenu.vue'
import SkeletonBlock from '@/reusables/SkeletonBlock.vue'
import type { AccountUserRead } from '@/types/api'

const { user: me } = useAuth()
const { users, devices, isLoading, isSaving, error, formError, create, setActive, setDevices, setPassword, remove } =
  useUsers()
const { date } = useFormat()

const adding = ref(false)
const editingGrants = ref<AccountUserRead | null>(null)
const settingPassword = ref<AccountUserRead | null>(null)
const confirmingDelete = ref<AccountUserRead | null>(null)

const form = ref({ username: '', display_name: '', password: '', device_ids: [] as string[] })
const grantSelection = ref<string[]>([])
const newPassword = ref('')

const query = ref('')

/** Owners first, then subaccounts; each filtered by name, username or email. */
const rows = computed(() => {
  const q = query.value.trim().toLowerCase()
  return [...users.value]
    .sort((a, b) => (a.role === b.role ? a.display_name.localeCompare(b.display_name) : a.role === 'owner' ? -1 : 1))
    .filter((u) => !q || [u.display_name, u.username, u.email ?? ''].some((v) => v.toLowerCase().includes(q)))
})

function toggle(list: string[], id: string) {
  const at = list.indexOf(id)
  at >= 0 ? list.splice(at, 1) : list.push(id)
}

async function onCreate() {
  if (await create({ ...form.value })) {
    adding.value = false
    form.value = { username: '', display_name: '', password: '', device_ids: [] }
  }
}

function openGrants(u: AccountUserRead) {
  grantSelection.value = [...u.device_ids]
  editingGrants.value = u
}

async function saveGrants() {
  if (editingGrants.value && (await setDevices(editingGrants.value.id, grantSelection.value))) {
    editingGrants.value = null
  }
}

async function savePassword() {
  if (settingPassword.value && (await setPassword(settingPassword.value.id, newPassword.value))) {
    settingPassword.value = null
    newPassword.value = ''
  }
}

async function onDelete() {
  if (confirmingDelete.value && (await remove(confirmingDelete.value.id))) {
    confirmingDelete.value = null
  }
}

/** Two letters at most, never an empty circle — as in the sidebar. */
function initials(name: string): string {
  return name.split(/\s+/).slice(0, 2).map((part) => part.charAt(0).toUpperCase()).join('') || '?'
}

const MENU_ITEM = 'flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm hover:bg-surface'
const BADGE = 'inline-flex items-center rounded-full px-2 py-0.5 text-[12px] leading-5 whitespace-nowrap ring-1 ring-inset'

const TONES = {
  green: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  brand: 'bg-brand-soft text-brand ring-brand/20',
  muted: 'bg-surface text-ink-muted ring-line',
} as const

/** What someone can reach, as badges: Owner, their screens, and Deactivated when they are. */
function badges(u: AccountUserRead): { label: string; tone: keyof typeof TONES }[] {
  const out: { label: string; tone: keyof typeof TONES }[] = []
  if (u.role === 'owner') out.push({ label: 'Owner', tone: 'green' })
  out.push({ label: reach(u), tone: u.role === 'owner' || u.device_count ? 'brand' : 'muted' })
  if (!u.is_active) out.push({ label: 'Deactivated', tone: 'muted' })
  return out
}

function reach(u: AccountUserRead): string {
  if (u.role === 'owner') return 'All screens'
  if (!u.device_count) return 'No screens'
  return `${u.device_count} screen${u.device_count === 1 ? '' : 's'}`
}
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Header row: what this is and how many, then find and add. -->
    <div class="flex flex-wrap items-center gap-3">
      <h2 class="mr-auto text-lg text-ink">
        All users <span class="text-ink-subtle">{{ users.length }}</span>
      </h2>
      <label class="relative order-last block w-full sm:order-none sm:w-64">
        <IconSearch class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-subtle" />
        <input
          v-model="query"
          type="search"
          placeholder="Search"
          aria-label="Search users"
          class="h-9 w-full rounded-lg border border-line-strong bg-canvas pr-3 pl-9 text-sm text-ink
                 placeholder:text-ink-subtle focus:border-ink focus:outline-none"
        />
      </label>
      <AppButton size="sm" @click="adding = true">
        <IconAdd class="size-4" aria-hidden="true" />
        Add user
      </AppButton>
    </div>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>

    <!-- No horizontal scroll container: it would clip the ⋮ menus. Columns drop out on
         narrow screens instead. -->
    <div class="rounded-2xl bg-canvas">
      <table class="w-full table-fixed text-left text-sm">
        <thead class="text-[12px] text-ink-muted">
          <tr class="bg-surface">
            <th class="rounded-tl-2xl px-4 py-3 font-normal">User name</th>
            <th class="hidden w-56 px-4 py-3 font-normal sm:table-cell">Access</th>
            <th class="hidden w-32 px-4 py-3 font-normal md:table-cell">Date added</th>
            <th class="w-14 rounded-tr-2xl px-2 py-3"><span class="sr-only">Actions</span></th>
          </tr>
        </thead>

        <tbody v-if="isLoading && !users.length" class="divide-y divide-line" aria-busy="true">
          <tr v-for="i in 3" :key="i">
            <td class="px-4 py-3.5">
              <div class="flex items-center gap-3">
                <SkeletonBlock class="size-9 shrink-0 rounded-full" />
                <div class="min-w-0 flex-1">
                  <SkeletonBlock class="h-3.5 w-32 max-w-full rounded-md" />
                  <SkeletonBlock class="mt-1.5 h-3 w-24 max-w-full rounded-md" />
                </div>
              </div>
            </td>
            <td class="hidden px-4 py-3.5 sm:table-cell"><SkeletonBlock class="h-5 w-20 rounded-full" /></td>
            <td class="hidden px-4 py-3.5 md:table-cell"><SkeletonBlock class="h-3 w-20 rounded-md" /></td>
            <td />
          </tr>
        </tbody>

        <tbody v-else class="divide-y divide-line">
          <tr v-for="u in rows" :key="u.id">
            <td class="px-4 py-3">
              <div class="flex min-w-0 items-center gap-3" :class="!u.is_active && 'opacity-60'">
                <span
                  class="flex size-9 shrink-0 items-center justify-center rounded-full text-[12px] font-medium"
                  :class="u.role === 'owner' ? 'bg-brand text-ink-inverse' : 'bg-brand-soft text-brand'"
                  aria-hidden="true"
                >
                  {{ initials(u.display_name) }}
                </span>
                <div class="min-w-0">
                  <p class="truncate font-medium text-ink">
                    {{ u.display_name }}
                    <span v-if="u.id === me?.id" class="font-normal text-ink-subtle"> · you</span>
                  </p>
                  <p class="truncate text-[13px] text-ink-muted">{{ u.email ?? `@${u.username}` }}</p>
                  <!-- Phones: no Access column, so the badges go here. -->
                  <div class="mt-1.5 flex flex-wrap gap-1 sm:hidden">
                    <span v-for="b in badges(u)" :key="b.label" :class="[BADGE, TONES[b.tone]]">{{ b.label }}</span>
                  </div>
                </div>
              </div>
            </td>
            <td class="hidden px-4 py-3 sm:table-cell">
              <div class="flex flex-wrap gap-1">
                <span v-for="b in badges(u)" :key="b.label" :class="[BADGE, TONES[b.tone]]">{{ b.label }}</span>
              </div>
            </td>
            <td class="hidden px-4 py-3 whitespace-nowrap text-ink-muted md:table-cell">{{ date(u.created_at) }}</td>
            <td class="px-2 py-3">
              <OverflowMenu
                v-if="u.role !== 'owner'"
                v-slot="{ close }"
                class="ml-auto w-fit"
                :label="`Actions for ${u.display_name}`"
              >
                <button type="button" role="menuitem" :class="[MENU_ITEM, 'text-ink']" @click="close(); openGrants(u)">
                  <IconTvOutline class="size-4 shrink-0 text-ink-muted" aria-hidden="true" />Change screens
                </button>
                <button type="button" role="menuitem" :class="[MENU_ITEM, 'text-ink']" @click="close(); settingPassword = u">
                  <IconKeyOutline class="size-4 shrink-0 text-ink-muted" aria-hidden="true" />Set password
                </button>
                <button
                  type="button" role="menuitem" :class="[MENU_ITEM, 'text-ink']" :disabled="isSaving"
                  @click="close(); setActive(u.id, !u.is_active)"
                >
                  <component
                    :is="u.is_active ? IconPersonOffOutline : IconPersonCheckOutline"
                    class="size-4 shrink-0 text-ink-muted" aria-hidden="true"
                  />
                  {{ u.is_active ? 'Deactivate' : 'Reactivate' }}
                </button>
                <button type="button" role="menuitem" :class="[MENU_ITEM, 'text-danger']" @click="close(); confirmingDelete = u">
                  <IconDeleteOutline class="size-4 shrink-0" aria-hidden="true" />Delete user
                </button>
              </OverflowMenu>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="4" class="px-4 py-10 text-center text-ink-muted">
              {{ query ? 'No users match your search.' : 'No users yet.' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create -->
    <AppModal v-if="adding" title="Add user" @close="adding = false">
      <form class="flex flex-col gap-3" @submit.prevent="onCreate">
        <AppInput id="u-username" v-model="form.username" label="Username" required
                  hint="They sign in with this — no email needed" />
        <AppInput id="u-name" v-model="form.display_name" label="Name" required />
        <AppInput id="u-password" v-model="form.password" label="Password" type="password"
                  required hint="At least 8 characters. You can change it later." />
        <div v-if="devices.length">
          <p class="mb-1 text-[13px] text-ink-muted">Screens they can manage</p>
          <ul class="max-h-40 overflow-y-auto">
            <li v-for="d in devices" :key="d.id">
              <label class="flex cursor-pointer items-center gap-2 rounded-lg p-1.5 hover:bg-surface">
                <input type="checkbox" class="size-4 accent-ink"
                       :checked="form.device_ids.includes(d.id)"
                       @change="toggle(form.device_ids, d.id)" />
                <span class="text-sm text-ink">{{ d.name || 'Unnamed screen' }}</span>
                <span v-if="d.location" class="text-[13px] text-ink-subtle">{{ d.location }}</span>
              </label>
            </li>
          </ul>
        </div>
        <p v-else class="text-[13px] text-ink-subtle">
          No screens yet — you can grant access once devices are paired.
        </p>
        <ModalActions>
          <AppButton variant="secondary" size="sm" type="button" @click="adding = false">Cancel</AppButton>
          <AppButton size="sm" type="submit" :loading="isSaving">Create</AppButton>
        </ModalActions>
      </form>
    </AppModal>

    <!-- Grants -->
    <AppModal v-if="editingGrants" :title="`Screens for ${editingGrants.display_name}`"
              @close="editingGrants = null">
      <p v-if="!devices.length" class="text-sm text-ink-muted">No screens yet.</p>
      <ul v-else class="max-h-64 overflow-y-auto">
        <li v-for="d in devices" :key="d.id">
          <label class="flex cursor-pointer items-center gap-2 rounded-lg p-1.5 hover:bg-surface">
            <input type="checkbox" class="size-4 accent-ink"
                   :checked="grantSelection.includes(d.id)"
                   @change="toggle(grantSelection, d.id)" />
            <span class="text-sm text-ink">{{ d.name || 'Unnamed screen' }}</span>
          </label>
        </li>
      </ul>
      <ModalActions>
        <AppButton variant="secondary" size="sm" @click="editingGrants = null">Cancel</AppButton>
        <AppButton size="sm" :loading="isSaving" @click="saveGrants">Save</AppButton>
      </ModalActions>
    </AppModal>

    <!-- Password -->
    <AppModal v-if="settingPassword" :title="`New password for ${settingPassword.display_name}`"
              @close="settingPassword = null">
      <p class="mb-3 text-[13px] text-ink-muted">
        There is no email reset — you set the password and pass it on.
      </p>
      <AppInput id="u-newpw" v-model="newPassword" label="Password" type="password" required />
      <ModalActions>
        <AppButton variant="secondary" size="sm" @click="settingPassword = null">Cancel</AppButton>
        <AppButton size="sm" :loading="isSaving" :disabled="newPassword.length < 8" @click="savePassword">
          Set password
        </AppButton>
      </ModalActions>
    </AppModal>

    <!-- Delete -->
    <AppModal v-if="confirmingDelete" title="Delete this user?" @close="confirmingDelete = null">
      <p class="text-sm text-ink-muted">
        {{ confirmingDelete.display_name }} will lose access immediately. Media and playlists they
        created are kept.
      </p>
      <ModalActions>
        <AppButton variant="secondary" size="sm" @click="confirmingDelete = null">Cancel</AppButton>
        <AppButton variant="danger" size="sm" :loading="isSaving" @click="onDelete">Delete</AppButton>
      </ModalActions>
    </AppModal>
  </div>
</template>
