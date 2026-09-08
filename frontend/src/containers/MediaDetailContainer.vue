<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useFormat } from '@/hooks/useFormat'
import { useMediaDetail } from '@/hooks/useMediaDetail'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppModal from '@/reusables/AppModal.vue'
import PageTitle from '@/reusables/PageTitle.vue'

const route = useRoute()
const router = useRouter()
const { media, isLoading, error, deleteError, isDeleting, remove } = useMediaDetail(
  String(route.params.id),
)
const { bytes, duration, dimensions, date } = useFormat()

const confirming = ref(false)

async function onDelete() {
  if (await remove()) {
    router.push({ name: 'media' })
  } else {
    // Keep the dialog closed so the 409 — which names the playlists — is readable on the page.
    confirming.value = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <AppButton variant="ghost" size="sm" class="self-start" @click="router.push({ name: 'media' })">
      ← Media
    </AppButton>

    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>
    <AppAlert v-else-if="error" tone="danger">{{ error }}</AppAlert>

    <template v-else-if="media">
      <PageTitle :title="media.filename" :subtitle="`Added ${date(media.created_at)}`">
        <template #actions>
          <AppButton variant="danger" size="sm" @click="confirming = true">Delete</AppButton>
        </template>
      </PageTitle>

      <AppAlert v-if="deleteError" tone="danger">{{ deleteError }}</AppAlert>

      <div class="overflow-hidden rounded-xl bg-surface">
        <video v-if="media.kind === 'video'" :src="media.url" controls class="max-h-[60vh] w-full" />
        <img v-else :src="media.url" :alt="media.filename" class="max-h-[60vh] w-full object-contain" />
      </div>

      <dl class="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
        <div>
          <dt class="text-[13px] text-ink-muted">Type</dt>
          <dd class="text-sm text-ink">{{ media.mime_type }}</dd>
        </div>
        <div>
          <dt class="text-[13px] text-ink-muted">Size</dt>
          <dd class="text-sm text-ink">{{ bytes(media.size_bytes) }}</dd>
        </div>
        <div>
          <dt class="text-[13px] text-ink-muted">Dimensions</dt>
          <dd class="text-sm text-ink">{{ dimensions(media.width, media.height) }}</dd>
        </div>
        <div v-if="media.kind === 'video'">
          <dt class="text-[13px] text-ink-muted">Duration</dt>
          <dd class="text-sm text-ink">{{ duration(media.duration_seconds) }}</dd>
        </div>
      </dl>

      <div>
        <p class="text-[13px] text-ink-muted">Used in</p>
        <p v-if="!media.used_in.length" class="text-sm text-ink-subtle">No playlists yet</p>
        <ul v-else class="mt-1 flex flex-wrap gap-2">
          <li
            v-for="name in media.used_in"
            :key="name"
            class="rounded-full bg-raised px-3 py-1 text-[13px] text-ink"
          >
            {{ name }}
          </li>
        </ul>
      </div>
    </template>

    <AppModal v-if="confirming" title="Delete this file?" @close="confirming = false">
      <p class="text-sm text-ink-muted">
        {{ media?.filename }} will be removed from the library and from storage. This cannot be
        undone.
      </p>
      <div class="mt-4 flex justify-end gap-2">
        <AppButton variant="secondary" size="sm" @click="confirming = false">Cancel</AppButton>
        <AppButton variant="danger" size="sm" :loading="isDeleting" @click="onDelete">
          Delete
        </AppButton>
      </div>
    </AppModal>
  </div>
</template>
