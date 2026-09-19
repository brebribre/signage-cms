import { describe, expect, it } from 'vitest'

import { canvasSize, fitRects } from '../src/ui/pictures'

describe('fitRects — the same rule as CSS object-fit', () => {
  const wide = { width: 4000, height: 2000 }
  const box = { width: 1000, height: 1000 }

  it('contain letterboxes inside the box, centred', () => {
    const r = fitRects(wide, box, 'contain')
    expect([r.dw, r.dh]).toEqual([1000, 500])
    expect([r.dx, r.dy]).toEqual([0, 250])
  })

  it('cover fills the box and lets the sides fall outside it', () => {
    const r = fitRects(wide, box, 'cover')
    expect([r.dw, r.dh]).toEqual([2000, 1000])
    expect([r.dx, r.dy]).toEqual([-500, 0])
  })

  it('fill stretches to the box', () => {
    const r = fitRects(wide, box, 'fill')
    expect([r.dx, r.dy, r.dw, r.dh]).toEqual([0, 0, 1000, 1000])
  })

  it('always draws the whole source', () => {
    for (const fit of ['contain', 'cover', 'fill'] as const) {
      const r = fitRects(wide, box, fit)
      expect([r.sx, r.sy, r.sw, r.sh]).toEqual([0, 0, 4000, 2000])
    }
  })
})

describe('canvasSize — device pixels, capped', () => {
  it('follows the box at a device pixel ratio of 1', () => {
    expect(canvasSize({ width: 1920, height: 1080 })).toEqual({ width: 1920, height: 1080 })
  })

  it('never exceeds the largest side a TV browser will paint', () => {
    const size = canvasSize({ width: 8000, height: 4500 })
    expect(Math.max(size.width, size.height)).toBeLessThanOrEqual(4096)
    expect(size.width / size.height).toBeCloseTo(8000 / 4500, 2)
  })

  it('never collapses to nothing', () => {
    expect(canvasSize({ width: 0.2, height: 0.1 })).toEqual({ width: 1, height: 1 })
  })
})
