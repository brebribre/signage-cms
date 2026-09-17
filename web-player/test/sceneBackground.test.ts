import { describe, expect, it } from 'vitest'

import type { ManifestSlot } from '../src/api'
import { blurSource } from '../src/sceneBackground'

const el = (id: string, kind: string, width = 1, height = 1) => ({ id, kind, url: id, checksum: id, bytes: 1, width, height })

describe('blurSource — the same rule as the CMS preview', () => {
  it('is nothing for a black scene', () => {
    expect(blurSource({ id: 's', duration_seconds: 5, elements: [el('a', 'image')] })).toBeNull()
  })

  it('picks the biggest box, bottom-most on a tie, never a website', () => {
    const slot: ManifestSlot = {
      id: 's', duration_seconds: 5, background: 'blur',
      elements: [el('web', 'web', 1, 1), el('small', 'image', 0.2, 0.2), el('big', 'video', 0.5, 0.9), el('tie', 'image', 0.9, 0.5)],
    }
    expect(blurSource(slot)?.id).toBe('big')
  })
})
