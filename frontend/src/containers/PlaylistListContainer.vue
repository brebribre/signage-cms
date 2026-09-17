<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import IconAdd from '~icons/material-symbols/add'
import IconArrowBack from '~icons/material-symbols/arrow-back'

import { useFormat } from '@/hooks/useFormat'
import { usePlaylists } from '@/hooks/usePlaylists'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppCard from '@/reusables/AppCard.vue'
import AppInput from '@/reusables/AppInput.vue'
import AppModal from '@/reusables/AppModal.vue'
import EmptyState from '@/reusables/EmptyState.vue'
import ModalActions from '@/reusables/ModalActions.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import { returnLabel, safeReturnPath } from '@/utils/returnTo'

const route = useRoute()
const router = useRouter()
const { items, isLoading, isCreating, error, create } = usePlaylists()
const { duration, date } = useFormat()

/** Set when the deploy flow sent someone here to make a playlist — carried into the editor, so
 *  its Save brings them straight back with the new playlist picked. */
const returnTo = safeReturnPath(route.query.returnTo)

const adding = ref(route.query.new === '1')
const newName = ref('')
// Opened once; a reload shouldn't keep reopening the dialog.
if (route.query.new) router.replace({ query: { ...route.query, new: undefined } })

async function onCreate() {
  const id = await create(newName.value)
  if (id) {
    adding.value = false
    newName.value = ''
    router.push({ name: 'playlist-detail', params: { id }, query: returnTo ? { returnTo } : {} })
  }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <AppButton
      v-if="returnTo"
      variant="ghost" size="sm" class="self-start"
      @click="router.push({ path: returnTo, query: { returned: '1' } })"
    >
      <IconArrowBack class="size-4" />
      {{ returnLabel(returnTo) }}
    </AppButton>

    <PageTitle title="Playlists" :subtitle="`${items.length} playlist${items.length === 1 ? '' : 's'}`">
      <template #actions>
        <AppButton size="sm" @click="adding = true">
          <IconAdd class="size-4" aria-hidden="true" />
          New playlist
        </AppButton>
      </template>
    </PageTitle>

    <AppAlert v-if="error" tone="danger">{{ error }}</AppAlert>
    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>

    <EmptyState
      v-else-if="!items.length"
      title="No playlists yet"
      description="A playlist is an ordered list of media with a duration for each slot."
    >
      <template #actions>
        <AppButton size="sm" @click="adding = true">
          <IconAdd class="size-4" aria-hidden="true" />
          New playlist
        </AppButton>
      </template>
    </EmptyState>

    <div v-else class="flex flex-col gap-2">
      <AppCard
        v-for="p in items"
        :key="p.id"
        interactive
        @click="router.push({ name: 'playlist-detail', params: { id: p.id } })"
      >
        <div class="flex items-center gap-4">
          <div class="min-w-0 flex-1">
            <p class="truncate text-base text-ink">{{ p.name }}</p>
            <p class="mt-0.5 text-[13px] text-ink-muted">
              {{ p.item_count }} item{{ p.item_count === 1 ? '' : 's' }} ·
              {{ duration(p.total_duration_seconds) }}
              <span v-if="p.shuffle"> · shuffled</span>
              · updated {{ date(p.updated_at) }}
            </p>
          </div>
          <div v-if="p.thumbnails.length" class="flex max-w-[13rem] shrink-0 gap-1.5 overflow-x-auto">
            <div
              v-for="(url, i) in p.thumbnails"
              :key="i"
              class="size-14 shrink-0 overflow-hidden rounded-lg bg-raised"
            >
              <img v-if="url" :src="url" class="size-full object-cover" loading="lazy" />
            </div>
          </div>
          <span class="shrink-0 text-ink-subtle" aria-hidden="true">›</span>
        </div>
      </AppCard>
    </div>

    <AppModal v-if="adding" title="New playlist" @close="adding = false">
      <form @submit.prevent="onCreate">
        <AppInput id="playlist-name" v-model="newName" label="Name" required />
        <ModalActions>
          <AppButton variant="secondary" size="sm" type="button" @click="adding = false">
            Cancel
          </AppButton>
          <AppButton size="sm" type="submit" :loading="isCreating" :disabled="!newName.trim()">
            Create
          </AppButton>
        </ModalActions>
      </form>
    </AppModal>
  </div>
</template>
