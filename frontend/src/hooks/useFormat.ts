/** Presentation formatting. Pure, so containers can call it without owning the rules. */
export function useFormat() {
  function bytes(value: number): string {
    if (value < 1024) return `${value} B`
    const units = ['KB', 'MB', 'GB']
    let v = value / 1024
    let i = 0
    while (v >= 1024 && i < units.length - 1) {
      v /= 1024
      i++
    }
    return `${v < 10 ? v.toFixed(1) : Math.round(v)} ${units[i]}`
  }

  function duration(seconds: number | null | undefined): string {
    // Only an *absent* duration is an em-dash. A real zero is a real length — an empty
    // playlist reads "0:00 loop", not "— loop".
    if (seconds === null || seconds === undefined) return '—'
    const total = Math.round(seconds)
    const m = Math.floor(total / 60)
    const s = total % 60
    return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `0:${String(s).padStart(2, '0')}`
  }

  function dimensions(w: number | null, h: number | null): string {
    return w && h ? `${w}×${h}` : '—'
  }

  function date(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  }

  return { bytes, duration, dimensions, date }
}
