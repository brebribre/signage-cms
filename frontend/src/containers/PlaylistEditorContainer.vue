<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import IconDeleteOutline from '~icons/material-symbols/delete-outline'
import IconDragIndicator from '~icons/material-symbols/drag-indicator'
import IconEditSquareOutline from '~icons/material-symbols/edit-square-outline'
import IconEdit from '~icons/material-symbols/edit-outline'
import IconClose from '~icons/material-symbols/close'
import IconCheck from '~icons/material-symbols/check'
import IconVisibility from '~icons/material-symbols/visibility'
import IconVisibilityOff from '~icons/material-symbols/visibility-off'
import IconArrowBack from '~icons/material-symbols/arrow-back'
import IconLanguage from '~icons/material-symbols/language'

import { useDevices } from '@/hooks/useDevices'
import { useFormat } from '@/hooks/useFormat'
import { useMedia } from '@/hooks/useMedia'
import { createEmptyItem, usePlaylistEditor } from '@/hooks/usePlaylistEditor'
import { usePlaylistPreview } from '@/hooks/usePlaylistPreview'
import { SCREEN_PRESETS, useScreenPresets } from '@/hooks/useScreenPresets'
import AddMediaMenu from '@/reusables/AddMediaMenu.vue'
import AppAlert from '@/reusables/AppAlert.vue'
import AppButton from '@/reusables/AppButton.vue'
import AppInput from '@/reusables/AppInput.vue'
import AppModal from '@/reusables/AppModal.vue'
import MediaPicker from '@/reusables/MediaPicker.vue'
import type { MediaRead, SceneBackground } from '@/types/api'
import ModalActions from '@/reusables/ModalActions.vue'
import DurationPicker from '@/reusables/DurationPicker.vue'
import OverflowMenu from '@/reusables/OverflowMenu.vue'
import SceneEditor from '@/reusables/SceneEditor.vue'
import ScreenPreview from '@/reusables/ScreenPreview.vue'
import PageTitle from '@/reusables/PageTitle.vue'
import type { DraftElement, DraftItem } from '@/hooks/usePlaylistEditor'
import { useSortableList } from '@/hooks/useSortableList'
import { returnLabel, safeReturnPath } from '@/utils/returnTo'
import { normalizeWebsiteUrl } from '@/utils/websiteUrl'

const route = useRoute()
const router = useRouter()
const id = String(route.params.id)

const {
  playlist, draft, draftName, isLoading, isSaving, isDirty, error, saveError, deleteError,
  totalSeconds, enabledCount, addMedia, addWebsite, removeAt, move, save, setShuffle, remove,
} = usePlaylistEditor(id)
const { items: library, isLoading: libraryLoading, prepend } = useMedia()
const { items: devices } = useDevices()
const { duration } = useFormat()
const { presetId, isCustom, customWidth, customHeight, screen, deviceOptions } =
  useScreenPresets(devices)
const preview = usePlaylistPreview(() => draft.value)

// Renaming, in place on the title. Enter or leaving the field keeps the new name for Save, like
// any other change to the playlist; Escape puts back the name it had before this edit.
const renaming = ref(false)
const nameInput = ref('')
const nameField = ref<HTMLInputElement | null>(null)
const renameButton = ref<HTMLButtonElement | null>(null)

async function startRename() {
  nameInput.value = draftName.value
  renaming.value = true
  await nextTick()
  nameField.value?.select()
}

async function finishRename(keep: boolean) {
  if (!renaming.value) return
  renaming.value = false
  // An emptied name isn't a name: keep the one it had.
  if (keep && nameInput.value.trim()) draftName.value = nameInput.value.trim()
  await nextTick()
  renameButton.value?.focus()
}

const picking = ref(false)
const confirmingDelete = ref(false)
/** Drag to reorder — see useSortableList. */
const listRef = ref<HTMLElement | null>(null)
const { dragging, onRowPointerDown, onHandlePointerDown, onHandleKeydown } = useSortableList({ list: listRef, move })

// The full-page canvas editor. `editingIsNew` tracks whether `editingItem` is still just a
// candidate — it only lands in `draft` once Apply gives it at least one element, so
// cancelling "Create custom" never leaves a stray empty scene in the list.
const editingItem = ref<DraftItem | null>(null)
const editingIsNew = ref(false)

/** Files dropped on the Add media button open the picker already uploading them, so the
 *  drop lands somewhere instead of being swallowed. */
const pickerFiles = ref<File[]>([])
function openPicker(files: File[] = []) {
  pickerFiles.value = files
  picking.value = true
}
function closePicker() {
  picking.value = false
  pickerFiles.value = []
}
function confirmPick(chosen: MediaRead[]) {
  addMedia(chosen)
  closePicker()
}

// "Add media" → Website: one address becomes its own full-bleed scene.
const addingWebsite = ref(false)
const websiteInput = ref('')
const websiteError = ref<string | null>(null)

function openAddWebsite() {
  websiteInput.value = ''
  websiteError.value = null
  addingWebsite.value = true
}

function confirmWebsite() {
  const url = normalizeWebsiteUrl(websiteInput.value)
  if (!url) {
    websiteError.value = 'Enter a full https:// address'
    return
  }
  addWebsite(url)
  addingWebsite.value = false
}

/** Set when this playlist was opened from the deploy flow's "New playlist" — Save then takes
 *  people straight back there with this playlist picked. See DeployContainer's detour. */
const returnTo = safeReturnPath(route.query.returnTo)

function backToReturn() {
  if (returnTo) router.push({ path: returnTo, query: { returned: '1' } })
}

async function saveAndReturn() {
  // Nothing added yet still counts: an empty playlist can be picked now and filled in later.
  if (isDirty.value && !(await save())) return
  if (returnTo) router.push({ path: returnTo, query: { playlist: id } })
}

async function onDelete() {
  if (!(await remove())) {
    confirmingDelete.value = false
    return
  }
  if (returnTo) backToReturn()
  else router.push({ name: 'playlists' })
}

function startEditScene(row: DraftItem) {
  editingIsNew.value = false
  editingItem.value = row
}

function startCreateCustom() {
  editingIsNew.value = true
  editingItem.value = createEmptyItem()
}

function applySceneEdit(elements: DraftElement[], background: SceneBackground) {
  if (!editingItem.value) return
  editingItem.value.elements = elements
  editingItem.value.background = background
  if (editingIsNew.value && elements.length) draft.value.push(editingItem.value)
  editingItem.value = null
}

function closeSceneEdit() {
  editingItem.value = null
}

/** A row's list label — the scene's first element, plus a count if there's more than one. */
function sceneLabel(item: DraftItem): string {
  if (!item.elements.length) return 'Empty scene'
  if (item.elements.length === 1) return item.elements[0].filename
  return `${item.elements[0].filename} +${item.elements.length - 1} more`
}
</script>

<template>
  <div class="flex flex-col gap-6">
    <AppButton v-if="returnTo" variant="ghost" size="sm" class="self-start" @click="backToReturn">
      <IconArrowBack class="size-4" />
      {{ returnLabel(returnTo) }}
    </AppButton>
    <AppButton v-else variant="ghost" size="sm" class="self-start" @click="router.push({ name: 'playlists' })">
      <IconArrowBack class="size-4" />
      Playlists
    </AppButton>

    <p v-if="isLoading" class="text-sm text-ink-muted">Loading…</p>
    <AppAlert v-else-if="error" tone="danger">{{ error }}</AppAlert>

    <template v-else-if="playlist">
      <PageTitle
        :title="playlist.name"
        :subtitle="`${enabledCount} item${enabledCount === 1 ? '' : 's'} · ${duration(totalSeconds)} loop`"
      >
        <template #title>
          <input
            v-if="renaming"
            ref="nameField"
            v-model="nameInput"
            aria-label="Playlist name"
            maxlength="120"
            class="-mx-2 w-full min-w-0 rounded-lg bg-canvas px-2 tracking-[inherit] text-ink outline-2
                   outline-brand focus:outline"
            @keydown.enter.prevent="finishRename(true)"
            @keydown.esc.prevent="finishRename(false)"
            @blur="finishRename(true)"
          />
          <button
            v-else
            ref="renameButton"
            type="button"
            class="group -mx-2 max-w-full rounded-lg px-2 text-left transition-colors duration-150
                   hover:bg-canvas focus-visible:outline-2 focus-visible:outline-brand-bright"
            :aria-label="`Rename ${draftName}`"
            @click="startRename"
          >
            {{ draftName }}
            <!-- Inline, so it follows the last word when the name wraps. -->
            <IconEdit
              class="ml-1 inline size-5 align-[-0.1em] text-ink-subtle transition-colors group-hover:text-ink sm:size-6"
              aria-hidden="true"
            />
          </button>
        </template>
        <template #actions>
          <div class="flex items-center gap-2">
            <AppButton variant="danger" size="sm" @click="confirmingDelete = true">
              <IconDeleteOutline class="size-4" />
              Delete
            </AppButton>
            <!-- Explicitly saved, never autosaved: rearranging a live playlist must not push
                 half-finished states onto a wall of screens. -->
            <AppButton v-if="returnTo" size="sm" :loading="isSaving" @click="saveAndReturn">
              <IconCheck v-if="!isSaving" class="size-4" />
              Save and return
            </AppButton>
            <AppButton v-else size="sm" :disabled="!isDirty" :loading="isSaving" @click="save">
              <IconCheck v-if="!isSaving" class="size-4" />
              {{ isDirty ? 'Save' : 'Saved' }}
            </AppButton>
          </div>
        </template>
      </PageTitle>

      <AppAlert v-if="saveError" tone="danger">{{ saveError }}</AppAlert>
      <AppAlert v-if="deleteError" tone="danger">{{ deleteError }}</AppAlert>
      <AppAlert v-if="playlist.used_by.length">
        Playing on {{ playlist.used_by.join(', ') }}. Saved changes reach the screens within 30
        seconds.
      </AppAlert>

      <div class="flex items-center justify-between gap-4">
        <label class="flex items-center gap-2 text-sm text-ink-muted">
          <input
            type="checkbox"
            :checked="playlist.shuffle"
            class="size-4 accent-ink"
            @change="setShuffle(($event.target as HTMLInputElement).checked)"
          />
          Shuffle
        </label>
      </div>

      <!-- The media list comes first — it's what you're here to work on. Reference device,
           preview and Save follow, in that order, as the steps that come after placing items. -->
      <!-- Items and Add media share one column, so the button sits exactly as far below the last
           item as the items sit from each other. An empty playlist is just the button. -->
      <div class="flex flex-col gap-2">
      <ul v-if="draft.length" ref="listRef" class="relative flex flex-col gap-2">
        <li
          v-for="(row, index) in draft"
          :key="row.key"
          :data-sort-key="row.key"
          class="flex cursor-pointer items-center gap-3 rounded-xl bg-surface p-3 transition-colors duration-200"
          :class="[
            // opacity < 1 promotes the row to its own stacking context, so its ⋮ menu needs an
            // explicit z-index here or it loses to AddMediaMenu's (later in the DOM, also
            // positioned) stacking context on DOM order alone and renders underneath it.
            !row.isEnabled && 'relative z-10 opacity-50',
            // Lifted while held: above its neighbours, tinted, and outlined in brand.
            dragging === index && 'relative z-30 cursor-grabbing bg-canvas ring-2 ring-brand',
            preview.current.value?.key === row.key && 'bg-raised ring-2 ring-ink',
          ]"
          @pointerdown="onRowPointerDown($event, index)"
          @click="preview.select(row)"
        >
          <div class="flex min-w-0 flex-1 items-center gap-3">
            <!-- The drag handle: any pointer drags from here (a finger only from here, so a swipe
                 on the row still scrolls), and ↑/↓ move the row from the keyboard. -->
            <button
              type="button"
              class="-ml-1 flex size-8 shrink-0 cursor-grab touch-none items-center justify-center rounded-md
                     text-ink-subtle select-none hover:bg-raised hover:text-ink focus-visible:outline-2
                     focus-visible:outline-brand-bright active:cursor-grabbing"
              :aria-label="`Move scene ${index + 1} of ${draft.length}. Drag, or use the up and down arrow keys.`"
              @click.stop
              @pointerdown.stop="onHandlePointerDown($event, index)"
              @keydown="onHandleKeydown($event, index)"
            >
              <IconDragIndicator class="size-4" aria-hidden="true" />
            </button>

            <div class="flex size-12 shrink-0 items-center justify-center overflow-hidden rounded-md bg-raised">
              <img
                v-if="row.elements[0]?.thumbnailUrl"
                :src="row.elements[0].thumbnailUrl"
                :alt="sceneLabel(row)"
                class="size-full object-cover"
              />
              <IconLanguage
                v-else-if="row.elements[0]?.kind === 'web'"
                class="size-5 text-ink-muted"
                :aria-label="sceneLabel(row)"
              />
            </div>

            <p class="min-w-0 flex-1 truncate text-[13px] text-ink-subtle">
              {{ row.elements.length }} element{{ row.elements.length === 1 ? '' : 's' }}
            </p>
          </div>

          <div class="flex shrink-0 items-center gap-1">
            <!-- Video plays to its own natural end — there's no trim yet, so the number here
                 would just be a promise the player doesn't keep. Everything else has no
                 natural length of its own, so it gets a real duration picker instead. -->
            <span
              v-if="row.elements[0]?.kind === 'video'"
              class="px-2 py-1 text-[13px] tabular-nums text-ink-subtle"
            >
              {{ duration(row.elements[0]?.mediaDuration ?? row.durationSeconds) }}
            </span>
            <DurationPicker v-else v-model="row.durationSeconds" />

            <!-- Wider screens: each action as its own button. -->
            <div class="hidden items-center gap-1 sm:flex">
              <AppButton variant="ghost" size="sm" @click.stop="startEditScene(row)">
                <IconEditSquareOutline class="size-4" />
                Edit scene
              </AppButton>
              <AppButton variant="ghost" size="sm" @click.stop="row.isEnabled = !row.isEnabled">
                <component :is="row.isEnabled ? IconVisibilityOff : IconVisibility" class="size-4" />
                {{ row.isEnabled ? 'Disable' : 'Enable' }}
              </AppButton>
              <AppButton variant="ghost" size="sm" @click.stop="removeAt(index)">
                <IconClose class="size-4" />
                Remove
              </AppButton>
            </div>

            <!-- Phones: the same three actions behind one ⋮ menu. -->
            <OverflowMenu v-slot="{ close }" class="sm:hidden" label="Item actions">
              <button
                type="button" role="menuitem"
                class="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-surface"
                @click="close(); startEditScene(row)"
              >
                <IconEditSquareOutline class="size-4 shrink-0 text-ink-muted" />Edit scene
              </button>
              <button
                type="button" role="menuitem"
                class="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-ink hover:bg-surface"
                @click="close(); row.isEnabled = !row.isEnabled"
              >
                <component :is="row.isEnabled ? IconVisibilityOff : IconVisibility" class="size-4 shrink-0 text-ink-muted" />
                {{ row.isEnabled ? 'Disable' : 'Enable' }}
              </button>
              <button
                type="button" role="menuitem"
                class="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm text-danger hover:bg-surface"
                @click="close(); removeAt(index)"
              >
                <IconClose class="size-4 shrink-0" />Remove
              </button>
            </OverflowMenu>
          </div>
        </li>
      </ul>

      <!-- One big Add media at the end of the list, where the next item would go. -->
      <AddMediaMenu
        variant="block"
        @use-existing="openPicker()"
        @files="openPicker"
        @add-website="openAddWebsite"
        @create-custom="startCreateCustom"
      />
      </div>

      <!-- Reference device + preview. What every "Placement" edit above is aimed at, and
           the last check before Save. -->
      <div class="flex flex-col gap-3 rounded-xl bg-surface p-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-2">
            <select
              v-model="presetId"
              :disabled="isCustom"
              class="rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px] text-ink
                     focus:border-ink focus:outline-none disabled:opacity-40"
            >
              <optgroup v-if="deviceOptions.length" label="Your screens">
                <option v-for="d in deviceOptions" :key="d.id" :value="d.id">{{ d.label }}</option>
              </optgroup>
              <optgroup label="Presets">
                <option v-for="p in SCREEN_PRESETS" :key="p.id" :value="p.id">{{ p.label }}</option>
              </optgroup>
            </select>
            <label class="flex items-center gap-1.5 text-[13px] text-ink-muted">
              <input v-model="isCustom" type="checkbox" class="size-3.5 accent-ink" />
              Custom
            </label>
            <template v-if="isCustom">
              <input
                v-model.number="customWidth"
                type="number"
                min="1"
                class="w-20 rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px]
                       focus:border-ink focus:outline-none"
              />
              <span class="text-[13px] text-ink-subtle">×</span>
              <input
                v-model.number="customHeight"
                type="number"
                min="1"
                class="w-20 rounded-md border border-line-strong bg-canvas px-2 py-1 text-[13px]
                       focus:border-ink focus:outline-none"
              />
            </template>
          </div>
        </div>

        <!-- Unloaded while the scene editor covers the page: its websites would otherwise stay
             loaded twice, under the editor's own — too much for a phone. -->
        <ScreenPreview
          v-if="!editingItem"
          :screen-width="screen.width"
          :screen-height="screen.height"
          :elements="preview.current.value?.elements ?? []"
          :background="preview.current.value?.background ?? 'black'"
        />
      </div>
    </template>

    <MediaPicker
      v-if="picking"
      :library="library"
      :is-loading="libraryLoading"
      :initial-files="pickerFiles"
      @close="closePicker"
      @confirm="confirmPick"
      @uploaded="prepend"
    />

    <AppModal v-if="addingWebsite" title="Add website" @close="addingWebsite = false">
      <form @submit.prevent="confirmWebsite">
        <AppInput
          id="website-url"
          v-model="websiteInput"
          label="Address"
          placeholder="example.com"
          :error="websiteError"
          hint="Some sites refuse to be embedded and stay blank."
          required
        />
        <ModalActions>
          <AppButton variant="secondary" size="sm" type="button" @click="addingWebsite = false">Cancel</AppButton>
          <AppButton size="sm" type="submit">
            <IconCheck class="size-4" />
            Add
          </AppButton>
        </ModalActions>
      </form>
    </AppModal>

    <AppModal v-if="confirmingDelete" title="Delete this playlist?" @close="confirmingDelete = false">
      <p class="text-sm text-ink-muted">
        {{ playlist?.name }} will be removed. The media it contains is not affected.
      </p>
      <ModalActions>
        <AppButton variant="secondary" size="sm" @click="confirmingDelete = false">Cancel</AppButton>
        <AppButton variant="danger" size="sm" @click="onDelete">Delete</AppButton>
      </ModalActions>
    </AppModal>

    <!-- The scene canvas is a full page, not a modal: it needs the room, and it's the same
         editor whether you got here from "Edit scene" on an existing row or "Create custom"
         on a brand new one (editingIsNew just decides whether Apply also inserts the row). -->
    <div v-if="editingItem" class="fixed inset-0 z-40 bg-canvas">
      <SceneEditor
        :item="editingItem"
        :reference-screen="screen"
        :library="library"
        @uploaded="prepend"
        @apply="applySceneEdit"
        @close="closeSceneEdit"
      />
    </div>
  </div>
</template>
