<script setup lang="ts">
/**
 * The last question before a save reaches real screens. A playlist edit or a campaign save is
 * not a draft — screens pick it up within seconds — and the moment that's easiest to forget is
 * exactly the routine one: a quick reorder on a playlist that happens to be on the lobby wall.
 * Names the screens, so "3 screens" is never a surprise. Presentational only.
 */
import AppButton from '@/reusables/AppButton.vue'
import AppModal from '@/reusables/AppModal.vue'
import ModalActions from '@/reusables/ModalActions.vue'

defineProps<{
  /** What is about to change, as a noun: "this playlist", "this campaign". */
  what: string
  /** The screens that will change, by name. */
  screens: string[]
  /** The confirm button's label — the same word the button that opened this had. */
  action: string
  loading?: boolean
  /** The caller is a manager: the save is sent to the owner, not published. Same question,
   *  honest answer. */
  review?: boolean
}>()
const emit = defineEmits<{ confirm: []; cancel: [] }>()
</script>

<template>
  <AppModal :title="review ? 'Send for review?' : 'Publish to screens?'" @close="emit('cancel')">
    <p v-if="review" class="text-sm text-ink-muted">
      Saving {{ what }} would change what
      <b class="text-ink">{{ screens.length }} screen{{ screens.length === 1 ? '' : 's' }}</b>
      {{ screens.length === 1 ? 'is' : 'are' }} showing, so it goes to the owner first. Nothing
      changes on the screens until they approve it.
    </p>
    <p v-else class="text-sm text-ink-muted">
      Saving {{ what }} changes what
      <b class="text-ink">{{ screens.length }} screen{{ screens.length === 1 ? '' : 's' }}</b>
      {{ screens.length === 1 ? 'is' : 'are' }} showing. They pick it up within a few seconds.
    </p>
    <ul class="mt-3 flex flex-wrap gap-2">
      <li v-for="name in screens" :key="name" class="rounded-full bg-raised px-3 py-1 text-[13px] text-ink">
        {{ name }}
      </li>
    </ul>
    <ModalActions>
      <AppButton variant="secondary" size="sm" :disabled="loading" @click="emit('cancel')">Cancel</AppButton>
      <AppButton size="sm" :loading="loading" @click="emit('confirm')">{{ action }}</AppButton>
    </ModalActions>
  </AppModal>
</template>
