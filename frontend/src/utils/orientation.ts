import type { DeviceOrientation } from '@/types/api'

/**
 * A screen's mounting, as the rotation the player applies to its content — clockwise, from the
 * panel's own landscape. Degrees rather than portrait/landscape because a totem can be stood on
 * either side, and those are two different rotations that "portrait" alone could never tell
 * apart: the wrong one shows everything upside down.
 */
export const ORIENTATIONS: ReadonlyArray<{ value: DeviceOrientation; label: string; hint: string }> = [
  { value: '0', label: '0°', hint: 'Landscape' },
  { value: '90', label: '90°', hint: 'Portrait, top on the right' },
  { value: '180', label: '180°', hint: 'Landscape, upside down' },
  { value: '270', label: '270°', hint: 'Portrait, top on the left' },
]

export const isPortrait = (o: DeviceOrientation): boolean => o === '90' || o === '270'

export function orientationLabel(o: DeviceOrientation): string {
  const found = ORIENTATIONS.find((x) => x.value === o)
  return found ? `${found.label} · ${found.hint}` : o
}
