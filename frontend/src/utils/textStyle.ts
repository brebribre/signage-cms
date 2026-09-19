import type { CSSProperties } from 'vue'

import type { TextStyle } from '@/types/api'

/** The defaults every player uses — the same as the backend's TextStyle. */
export const TEXT_DEFAULT_STYLE: TextStyle = {
  size: 0.06, color: '#FFFFFF', weight: 'bold', align: 'center', background: null,
}

/** Canva's three starting sizes, as fractions of the screen's height. */
export const TEXT_PRESETS = [
  { label: 'Heading', size: 0.12 },
  { label: 'Subheading', size: 0.07 },
  { label: 'Body', size: 0.045 },
] as const

/** One rule for how a text box is drawn, shared by the scene editor, the preview and (in their
 *  own languages) the players: the box carries the background, the text sits vertically centred,
 *  wraps inside the box, and is aligned as asked. `frameHeight` is the rendered height of the
 *  screen frame in CSS pixels — the size is a fraction of it. */
export function textBoxStyle(style: TextStyle, frameHeight: number): CSSProperties {
  const px = Math.max(1, style.size * frameHeight)
  return {
    position: 'absolute',
    inset: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: style.align === 'left' ? 'flex-start' : style.align === 'right' ? 'flex-end' : 'center',
    padding: `${px * 0.25}px`,
    boxSizing: 'border-box',
    overflow: 'hidden',
    background: style.background ?? 'transparent',
    color: style.color,
    fontSize: `${px}px`,
    fontWeight: style.weight === 'bold' ? 700 : 400,
    lineHeight: 1.2,
    textAlign: style.align,
    whiteSpace: 'pre-wrap',
    overflowWrap: 'anywhere',
    fontFamily: "'Inter Variable', 'Helvetica Neue', Arial, sans-serif",
  }
}

/** A short name for a text element in lists — its first words. */
export function textLabel(text: string): string {
  const line = text.trim().split(/\n/)[0] ?? ''
  return line.length > 40 ? `${line.slice(0, 40)}…` : line || 'Text'
}
