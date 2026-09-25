import { describe, expect, it } from 'vitest'

import { fileRect, resolveCropRect } from './crop'

const close = (a: number, b: number) => expect(a).toBeCloseTo(b, 6)

describe('resolveCropRect', () => {
  it('with no crop is a centred cover', () => {
    // A 4:3 picture in a 16:9 box: full width, the middle three quarters of the height.
    const r = resolveCropRect(4000, 3000, 16 / 9)
    close(r.x, 0); close(r.w, 1)
    close(r.h, (4 / 3) / (16 / 9)); close(r.y, (1 - r.h) / 2)
  })
  it('keeps a window panned to the edge on the picture', () => {
    const r = resolveCropRect(1000, 1000, 1, 0, 1, 2)
    close(r.x, 0); close(r.y, 0.5); close(r.w, 0.5); close(r.h, 0.5)
  })
})

describe('fileRect', () => {
  it('is the resolved window when nothing is turned', () => {
    const r = fileRect(1920, 1080, 800, 450, { cropX: 0.3, cropY: 0.4, cropZoom: 2, rotation: 0 })
    const e = resolveCropRect(1920, 1080, 800 / 450, 0.3, 0.4, 2)
    expect(r).toEqual(e)
  })

  // A window chosen in the turned picture must land on the same pixels of the stored file.
  // Check it with a point: the window's top-left corner as seen on screen, turned back.
  it.each([90, 180, 270])('turns the window back into the file for %i°', (rotation) => {
    const fileW = 3000
    const fileH = 2000
    const swapped = rotation === 90 || rotation === 270
    const innerW = 600
    const innerH = 900
    const spec = { cropX: 0.35, cropY: 0.6, cropZoom: 1.5, rotation }
    const shown = resolveCropRect(swapped ? fileH : fileW, swapped ? fileW : fileH,
      swapped ? innerH / innerW : innerW / innerH, 0.35, 0.6, 1.5)
    const r = fileRect(fileW, fileH, innerW, innerH, spec)
    // Area is preserved, and the file-space window has the inner box's own shape in pixels.
    close(r.w * r.h, shown.w * shown.h)
    close((r.w * fileW) / (r.h * fileH), innerW / innerH)
    // The file point at the window's file-space centre shows at the shown window's centre.
    const px = r.x + r.w / 2
    const py = r.y + r.h / 2
    const onScreen = rotation === 90 ? [1 - py, px] : rotation === 180 ? [1 - px, 1 - py] : [py, 1 - px]
    close(onScreen[0], shown.x + shown.w / 2)
    close(onScreen[1], shown.y + shown.h / 2)
  })
})
