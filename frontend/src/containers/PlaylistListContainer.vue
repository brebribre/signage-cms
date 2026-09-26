<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import IconAdd from '~icons/material-symbols/add'
import IconArrowBack from '~icons/material-symbols/arrow-back'
import IconSearch from '~icons/material-symbols/search'

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
import ListRowSkeleton from '@/reusables/ListRowSkeleton.vue'
import SkeletonList from '@/reusables/SkeletonList.vue'
import ThumbnailStrip from '@/reusables/ThumbnailStrip.vue'
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

/** Search by name — as you type, newest-changed first as before. */
const query = ref('')
const visible = computed(() => {
  const q = query.value.trim().toLowerCase()
  return q ? items.value.filter((p) => p.name.toLowerCase().includes(q)) : items.value
})

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
    <SkeletonList v-if="isLoading" label="Loading playlists">
      <ListRowSkeleton :thumbnails="3" />
    </SkeletonList>

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

    <template v-else>
    <label class="relative block sm:w-72">
      <IconSearch class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-ink-subtle" aria-hidden="true" />
      <input
        v-model="query"
        type="search"
        placeholder="Search playlists"
        aria-label="Search playlists by name"
        class="w-full rounded-lg border border-line-strong bg-canvas py-2 pr-3 pl-9 text-sm text-ink
               focus:border-brand focus:outline-none"
      />
    </label>

    <EmptyState
      v-if="!visible.length"
      title="No playlists match"
      :description="`Nothing is called “${query.trim()}”.`"
    >
      <template #actions>
        <AppButton variant="secondary" size="sm" @click="query = ''">Show all playlists</AppButton>
      </template>
    </EmptyState>

    <div v-else class="flex flex-col gap-2">
      <AppCard
        v-for="p in visible"
        :key="p.id"
        interactive
        @click="router.push({ name: 'playlist-detail', params: { id: p.id } })"
      >
        <!-- The details come first and wrap rather than truncate; the thumbnails take whatever
             width is left and fit as many as they can (see ThumbnailStrip). On a phone they sit
             under the details, across the full width. -->
        <div class="flex items-center gap-4">
          <div class="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
          <div class="min-w-0 sm:max-w-[60%] sm:shrink-0">
            <p class="truncate text-base text-ink">{{ p.name }}</p>
            <p class="mt-0.5 text-[13px] text-ink-muted">
              {{ p.item_count }} item{{ p.item_count === 1 ? '' : 's' }} ·
              {{ duration(p.total_duration_seconds) }}
              <span v-if="p.shuffle"> · shuffled</span>
              · updated {{ date(p.updated_at) }}
            </p>
          </div>
          <ThumbnailStrip
            v-if="p.thumbnails.length"
            :thumbnails="p.thumbnails"
            :total="p.item_count"
            class="min-w-14 flex-1 justify-start sm:justify-end"
          />
          </div>
          <span class="shrink-0 text-ink-subtle" aria-hidden="true">›</span>
        </div>
      </AppCard>
    </div>
    </template>

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
