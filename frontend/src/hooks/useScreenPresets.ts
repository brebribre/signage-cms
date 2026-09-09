import { computed, ref, watch } from 'vue'
import type { Ref } from 'vue'

import type { DeviceRead } from '@/types/api'

export interface ScreenPreset {
  id: string
  label: string
  width: number
  height: number
}

/**
 * Fallback screen sizes to preview against, for when no real device fits — an account with
 * nothing paired yet, or sizing for a screen not yet purchased.
 *
 * Portrait is first-class here rather than an afterthought: tall 4K totems are one of the
 * commonest signage formats, and a landscape-only preview would quietly mislead about every
 * one of them.
 */
export const SCREEN_PRESETS: ScreenPreset[] = [
  { id: '4k-portrait', label: '4K portrait · 2160×3840', width: 2160, height: 3840 },
  { id: '4k-landscape', label: '4K landscape · 3840×2160', width: 3840, height: 2160 },
  { id: 'fhd-portrait', label: 'Full HD portrait · 1080×1920', width: 1080, height: 1920 },
  { id: 'fhd-landscape', label: 'Full HD landscape · 1920×1080', width: 1920, height: 1080 },
  { id: 'hd-landscape', label: 'HD landscape · 1366×768', width: 1366, height: 768 },
]

/** A real device's own dimensions win over guessing — this is what "select an existing
 *  device" resolves to. Prefixed `device:` in `presetId` to share one selector with presets. */
const DEVICE_PREFIX = 'device:'

const STORAGE_KEY = 'fortu.preview.screen'

/**
 * The reference screen a playlist is edited/previewed against.
 *
 * `devices` is optional so this hook still works standalone (e.g. a future preview page with
 * no device list at hand) — pass `useDevices().items` from a container to put real paired
 * screens first, which is the primary path once an account has any.
 */
export function useScreenPresets(devices?: Ref<DeviceRead[]>) {
  const presetId = ref<string>(SCREEN_PRESETS[0].id)
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

  // A screen that hasn't heartbeated yet has null dimensions — excluded, not shown as a
  // broken option with a blank size.
  const availableDevices = computed(() =>
    (devices?.value ?? []).filter((d) => d.paired_at && d.screen_width && d.screen_height),
  )

  const deviceOptions = computed(() =>
    availableDevices.value.map((d) => ({
      id: `${DEVICE_PREFIX}${d.id}`,
      label: `${d.name} · ${d.screen_width}×${d.screen_height}`,
    })),
  )

  const screen = computed(() => {
    if (isCustom.value) {
      return {
        width: Math.max(1, customWidth.value),
        height: Math.max(1, customHeight.value),
        label: `Custom · ${customWidth.value}×${customHeight.value}`,
      }
    }
    if (presetId.value.startsWith(DEVICE_PREFIX)) {
      const id = presetId.value.slice(DEVICE_PREFIX.length)
      const device = availableDevices.value.find((d) => d.id === id)
      if (device) {
        return {
          width: device.screen_width!,
          height: device.screen_height!,
          label: `${device.name} · ${device.screen_width}×${device.screen_height}`,
        }
      }
      // The remembered device is gone (unpaired, another account) — fall through to presets
      // rather than showing a stale/blank screen.
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

  return {
    presetId, isCustom, customWidth, customHeight, screen, isPortrait,
    deviceOptions,
  }
}
