import { computed, ref, watch } from 'vue'

export interface ScreenPreset {
  id: string
  label: string
  width: number
  height: number
}

/**
 * Screen sizes to preview against.
 *
 * Portrait is first-class here rather than an afterthought: tall 4K totems are one of the
 * commonest signage formats, and a landscape-only preview would quietly mislead about every
 * one of them.
 *
 * Phase 9 will add real registered devices to this list — `Device.screen_width` and
 * `screen_height` are already reported on every heartbeat, so "preview as Lobby screen"
 * becomes a lookup rather than a new mechanism.
 */
export const SCREEN_PRESETS: ScreenPreset[] = [
  { id: '4k-portrait', label: '4K portrait · 2160×3840', width: 2160, height: 3840 },
  { id: '4k-landscape', label: '4K landscape · 3840×2160', width: 3840, height: 2160 },
  { id: 'fhd-portrait', label: 'Full HD portrait · 1080×1920', width: 1080, height: 1920 },
  { id: 'fhd-landscape', label: 'Full HD landscape · 1920×1080', width: 1920, height: 1080 },
  { id: 'hd-landscape', label: 'HD landscape · 1366×768', width: 1366, height: 768 },
]

const STORAGE_KEY = 'fortu.preview.screen'

export function useScreenPresets() {
  const presetId = ref(SCREEN_PRESETS[0].id)
  const customWidth = ref(2160)
  const customHeight = ref(3840)
  const isCustom = ref(false)

  // Remembered per browser, because you preview against the same screen over and over and
  // re-picking it every visit is pure friction.
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      presetId.value = parsed.presetId ?? presetId.value
      isCustom.value = !!parsed.isCustom
      customWidth.value = parsed.customWidth ?? customWidth.value
      customHeight.value = parsed.customHeight ?? customHeight.value
    }
  } catch {
    /* private window, cleared storage, or blocked site data — defaults are fine */
  }

  const screen = computed(() => {
    if (isCustom.value) {
      return {
        width: Math.max(1, customWidth.value),
        height: Math.max(1, customHeight.value),
        label: `Custom · ${customWidth.value}×${customHeight.value}`,
      }
    }
    const preset = SCREEN_PRESETS.find((p) => p.id === presetId.value) ?? SCREEN_PRESETS[0]
    return { width: preset.width, height: preset.height, label: preset.label }
  })

  const isPortrait = computed(() => screen.value.height > screen.value.width)

  watch([presetId, isCustom, customWidth, customHeight], () => {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          presetId: presetId.value,
          isCustom: isCustom.value,
          customWidth: customWidth.value,
          customHeight: customHeight.value,
        }),
      )
    } catch {
      /* storage unavailable — the preview still works, it just will not be remembered */
    }
  })

  return { presetId, isCustom, customWidth, customHeight, screen, isPortrait }
}
