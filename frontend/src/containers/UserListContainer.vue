<script setup lang="ts">
import { computed, ref } from 'vue'
import IconSearch from '~icons/material-symbols/search'

import { useAuth } from '@/hooks/useAuth'
import { useFormat } from '@/hooks/useFormat'
import { useUsers } from '@/hooks/useUsers'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppInput from '@/reusables/AppInput.vue'
import AppModal from '@/reusables/AppModal.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import PageTitle from '@/reusables/PageTitle.vue'
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

function reach(u: AccountUserRead): string {
  if (u.role === 'owner') return 'All screens'
  if (!u.device_count) return 'No screens'
  return `${u.device_count} screen${u.device_count === 1 ? '' : 's'}`
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <PageTitle title="User Management">
      <template #actions>
        <AppButton size="sm" @click="adding = true">Create subaccount</AppButton>
      </template>
    </PageTitle>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>

    <label class="relative block sm:max-w-sm">
      <IconSearch class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-subtle" />
      <input
        v-model="query"
        type="search"
        placeholder="Search users"
        aria-label="Search users"
        class="h-9 w-full rounded-lg border border-line-strong bg-canvas pr-3 pl-9 text-sm text-ink
               placeholder:text-ink-subtle focus:border-ink focus:outline-none"
      />
    </label>

    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>

    <div v-else class="overflow-x-auto rounded-xl border border-line">
      <table class="w-full min-w-[720px] text-left text-sm">
        <thead class="bg-surface text-[12px] text-ink-muted">
          <tr>
            <th class="px-4 py-2.5 font-normal">Name</th>
            <th class="px-4 py-2.5 font-normal">Role</th>
            <th class="px-4 py-2.5 font-normal">Screens</th>
            <th class="px-4 py-2.5 font-normal">Status</th>
            <th class="px-4 py-2.5 font-normal">Created</th>
            <th class="px-4 py-2.5"><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-line">
          <tr v-for="u in rows" :key="u.id" :class="!u.is_active && 'text-ink-muted'">
            <td class="px-4 py-2.5">
              <p class="truncate text-ink" :class="!u.is_active && 'opacity-60'">
                {{ u.display_name }}
                <span v-if="u.id === me?.id" class="text-ink-subtle"> · you</span>
              </p>
              <p class="truncate text-[12px] text-ink-subtle">@{{ u.username }}</p>
            </td>
            <td class="px-4 py-2.5">{{ u.role === 'owner' ? 'Owner' : 'Subaccount' }}</td>
            <td class="px-4 py-2.5">
              <button
                v-if="u.role !== 'owner'"
                type="button"
                class="text-ink underline decoration-line-strong underline-offset-2 hover:decoration-ink"
                @click="openGrants(u)"
              >
                {{ reach(u) }}
              </button>
              <span v-else>{{ reach(u) }}</span>
            </td>
            <td class="px-4 py-2.5">
              <span class="inline-flex items-center gap-1.5">
                <span class="size-1.5 rounded-full" :class="u.is_active ? 'bg-emerald-600' : 'bg-ink-subtle'" />
                {{ u.is_active ? 'Active' : 'Deactivated' }}
              </span>
            </td>
            <td class="px-4 py-2.5 whitespace-nowrap text-ink-muted">{{ date(u.created_at) }}</td>
            <td class="px-4 py-2.5">
              <div v-if="u.role !== 'owner'" class="flex justify-end gap-1">
                <AppButton variant="ghost" size="sm" @click="settingPassword = u">Password</AppButton>
                <AppButton variant="ghost" size="sm" :loading="isSaving" @click="setActive(u.id, !u.is_active)">
                  {{ u.is_active ? 'Deactivate' : 'Reactivate' }}
                </AppButton>
                <AppButton variant="danger" size="sm" @click="confirmingDelete = u">Delete</AppButton>
              </div>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="6" class="px-4 py-8 text-center text-ink-muted">
              {{ query ? 'No users match your search.' : 'No users yet.' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create -->
    <AppModal v-if="adding" title="Create subaccount" @close="adding = false">
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
