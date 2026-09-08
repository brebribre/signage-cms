<script setup lang="ts">
import { computed, ref } from 'vue'

import { useAuth } from '@/hooks/useAuth'
import { useFormat } from '@/hooks/useFormat'
import { useUsers } from '@/hooks/useUsers'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import AppInput from '@/reusables/AppInput.vue'
import AppModal from '@/reusables/AppModal.vue'
import EmptyState from '@/reusables/EmptyState.vue'
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

const managers = computed(() => users.value.filter((u) => u.role === 'manager'))
const owners = computed(() => users.value.filter((u) => u.role === 'owner'))

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
    <PageTitle title="Users" subtitle="Owners reach every screen. Managers reach only what you grant.">
      <template #actions>
        <AppButton size="sm" @click="adding = true">Add user</AppButton>
      </template>
    </PageTitle>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <AppAlert v-if="formError" tone="danger">{{ formError }}</AppAlert>
    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>

    <template v-else>
      <div v-if="owners.length" class="flex flex-col gap-2">
        <p class="text-[13px] text-ink-muted">Owners</p>
        <AppCard v-for="u in owners" :key="u.id">
          <div class="flex items-center justify-between gap-4">
            <div class="min-w-0">
              <p class="truncate text-sm text-ink">
                {{ u.display_name }}
                <span class="text-ink-subtle">@{{ u.username }}</span>
                <span v-if="u.id === me?.id" class="text-ink-subtle"> · you</span>
              </p>
              <p class="text-[13px] text-ink-muted">All screens · since {{ date(u.created_at) }}</p>
            </div>
          </div>
        </AppCard>
      </div>

      <div class="flex flex-col gap-2">
        <p class="text-[13px] text-ink-muted">Managers</p>
        <EmptyState
          v-if="!managers.length"
          title="No managers yet"
          description="Add someone and grant them a subset of your screens."
        />
        <AppCard v-for="u in managers" :key="u.id">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="min-w-0" :class="!u.is_active && 'opacity-50'">
              <p class="truncate text-sm text-ink">
                {{ u.display_name }} <span class="text-ink-subtle">@{{ u.username }}</span>
                <span v-if="!u.is_active" class="text-ink-subtle"> · deactivated</span>
              </p>
              <p class="text-[13px] text-ink-muted">{{ reach(u) }} · since {{ date(u.created_at) }}</p>
            </div>
            <div class="flex shrink-0 flex-wrap items-center gap-1">
              <AppButton variant="ghost" size="sm" @click="openGrants(u)">Screens</AppButton>
              <AppButton variant="ghost" size="sm" @click="settingPassword = u">Password</AppButton>
              <AppButton variant="ghost" size="sm" :loading="isSaving" @click="setActive(u.id, !u.is_active)">
                {{ u.is_active ? 'Deactivate' : 'Reactivate' }}
              </AppButton>
              <AppButton variant="danger" size="sm" @click="confirmingDelete = u">Delete</AppButton>
            </div>
          </div>
        </AppCard>
      </div>
    </template>

    <!-- Add -->
    <AppModal v-if="adding" title="Add a manager" @close="adding = false">
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
          No screens registered yet — you can grant access once devices are paired.
        </p>
        <div class="mt-1 flex justify-end gap-2">
          <AppButton variant="secondary" size="sm" type="button" @click="adding = false">Cancel</AppButton>
          <AppButton size="sm" type="submit" :loading="isSaving">Create</AppButton>
        </div>
      </form>
    </AppModal>

    <!-- Grants -->
    <AppModal v-if="editingGrants" :title="`Screens for ${editingGrants.display_name}`"
              @close="editingGrants = null">
      <p v-if="!devices.length" class="text-sm text-ink-muted">
        No screens registered yet.
      </p>
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
      <div class="mt-4 flex justify-end gap-2">
        <AppButton variant="secondary" size="sm" @click="editingGrants = null">Cancel</AppButton>
        <AppButton size="sm" :loading="isSaving" @click="saveGrants">Save</AppButton>
      </div>
    </AppModal>

    <!-- Password -->
    <AppModal v-if="settingPassword" :title="`New password for ${settingPassword.display_name}`"
              @close="settingPassword = null">
      <p class="mb-3 text-[13px] text-ink-muted">
        There is no email reset — you set the password and pass it on.
      </p>
      <AppInput id="u-newpw" v-model="newPassword" label="Password" type="password" required />
      <div class="mt-4 flex justify-end gap-2">
        <AppButton variant="secondary" size="sm" @click="settingPassword = null">Cancel</AppButton>
        <AppButton size="sm" :loading="isSaving" :disabled="newPassword.length < 8" @click="savePassword">
          Set password
        </AppButton>
      </div>
    </AppModal>

    <!-- Delete -->
    <AppModal v-if="confirmingDelete" title="Delete this user?" @close="confirmingDelete = null">
      <p class="text-sm text-ink-muted">
        {{ confirmingDelete.display_name }} will lose access immediately. Media and playlists they
        created are kept.
      </p>
      <div class="mt-4 flex justify-end gap-2">
        <AppButton variant="secondary" size="sm" @click="confirmingDelete = null">Cancel</AppButton>
        <AppButton variant="danger" size="sm" :loading="isSaving" @click="onDelete">Delete</AppButton>
      </div>
    </AppModal>
  </div>
</template>
