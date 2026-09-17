/**
 * The size a website is laid out at in the CMS's previews, before being scaled down to fit.
 *
 * A screen's browser doesn't lay pages out at its panel's pixels: a 4K TV or Android box reports
 * about 1920×1080 to the page (a device pixel ratio of 2), so the longest side is capped at
 * [MAX_LAYOUT_PX], ratio kept. Besides matching what the screen shows, it keeps the preview
 * affordable — a phone laying out two or four desktop sites at 3840×2160 runs out of memory and
 * its browser tab goes white.
 */
const MAX_LAYOUT_PX = 1920

export function websiteLayoutScreen(width: number, height: number): { width: number; height: number } {
  const scale = Math.min(1, MAX_LAYOUT_PX / Math.max(width, height, 1))
  return { width: Math.round(width * scale), height: Math.round(height * scale) }
}
