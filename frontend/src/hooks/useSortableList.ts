import { nextTick, onBeforeUnmount, ref, type Ref } from 'vue'

/**
 * Drag-to-reorder for a vertical list, snappy and animated: the row you hold follows the pointer
 * exactly, and the others glide out of its way the moment it crosses one of them.
 *
 * One path for mouse, touch and pen (pointer events) — the browser's HTML5 drag and drop isn't
 * used at all: it never fires for a finger, drags a translucent ghost instead of the row, and
 * can't animate the rows it passes.
 *
 * - **Mouse** can grab anywhere on a row; the drag starts only after the pointer has moved a few
 *   pixels, so a plain click (and every button, picker or menu inside the row) still works.
 * - **Touch and pen** grab the handle only, so a swipe on the row still scrolls the page.
 * - **Keyboard**: ↑/↓ on the handle move the row one place, animated the same way.
 *
 * The rows animate with FLIP — measure where every row is, reorder, measure again, then play each
 * row from its old place to its new one — which works however tall each row is.
 *
 * Rows need `data-sort-key` (a stable key) and the list element `position: relative`, so every
 * row's offsetTop is measured from the list.
 */
export function useSortableList(options: {
  list: Ref<HTMLElement | null>
  /** Reorders the underlying array. */
  move: (from: number, to: number) => void
  /** The scroller to auto-scroll near its edges while dragging. Defaults to the nearest scrolling
   *  ancestor of the list. */
  scroller?: () => HTMLElement | null
}) {
  /** The index of the row being dragged, or null. */
  const dragging = ref<number | null>(null)

  const MOVE_MS = 180
  const DROP_MS = 160
  const START_THRESHOLD_PX = 4
  /** How far past a neighbour's midpoint the held row must go before they swap — stops two rows
   *  of different heights from swapping back and forth under a still pointer. */
  const HYSTERESIS_PX = 6
  const EDGE_PX = 64
  const MAX_SCROLL_PER_FRAME = 14

  let pointerId: number | null = null
  let startY = 0
  let pointerY = 0
  /** Where inside the held row it was grabbed, so it doesn't jump to put its top under the pointer. */
  let grabOffset = 0
  let pending: { index: number } | null = null
  let rowEl: HTMLElement | null = null
  let frame = 0

  const rows = () => Array.from(options.list.value?.querySelectorAll<HTMLElement>(':scope > [data-sort-key]') ?? [])

  function scrollerOf(): HTMLElement | null {
    if (options.scroller) return options.scroller()
    let el = options.list.value?.parentElement ?? null
    while (el) {
      const overflow = getComputedStyle(el).overflowY
      if (overflow === 'auto' || overflow === 'scroll') return el
      el = el.parentElement
    }
    return null
  }

  /** Reorder with FLIP. The held row is left alone: it is positioned by the pointer. */
  function animatedMove(from: number, to: number, held: HTMLElement | null) {
    const before = new Map(rows().map((el) => [el.dataset.sortKey!, el.getBoundingClientRect().top]))
    options.move(from, to)
    // Straight after Vue has patched the DOM and *before the browser paints*: waiting a frame here
    // let one frame show the rows already in their new places before the glide began — a flicker.
    void nextTick(() => {
      for (const el of rows()) {
        if (el === held) continue
        const old = before.get(el.dataset.sortKey!)
        if (old === undefined) continue
        // Relative to where it is laid out *now*, ignoring any transform still playing.
        const current = el.getBoundingClientRect().top - currentTranslate(el)
        const delta = old - current
        if (Math.abs(delta) < 0.5) continue
        el.style.transition = 'none'
        el.style.transform = `translateY(${delta}px)`
        void el.offsetHeight
        el.style.transition = `transform ${MOVE_MS}ms cubic-bezier(0.2, 0, 0, 1)`
        el.style.transform = ''
        clearTransitionLater(el, MOVE_MS)
      }
      // The held row's slot just moved: put it back under the pointer now, not on the next
      // pointer move — otherwise a pause mid-drag leaves it a row out of place.
      if (held && rowEl === held) held.style.transform = `translateY(${pointerY - grabOffset - layoutTop(held)}px)`
    })
  }

  /** Once an animation has played, hand the row's transition back to its own CSS. */
  function clearTransitionLater(el: HTMLElement, ms: number) {
    setTimeout(() => {
      if (el !== rowEl) el.style.transition = ''
    }, ms + 20)
  }

  function currentTranslate(el: HTMLElement): number {
    const t = getComputedStyle(el).transform
    return t && t !== 'none' ? new DOMMatrixReadOnly(t).m42 : 0
  }

  function layoutTop(el: HTMLElement): number {
    const list = options.list.value!
    return list.getBoundingClientRect().top + el.offsetTop
  }

  /** Follow the pointer, swap past midpoints, auto-scroll near edges — once per frame. */
  function tick() {
    frame = 0
    const index = dragging.value
    if (index === null || !rowEl) return

    const scroller = scrollerOf()
    if (scroller) {
      const bounds = scroller.getBoundingClientRect()
      const top = Math.max(bounds.top, 0)
      const bottom = Math.min(bounds.bottom, window.innerHeight)
      let dy = 0
      if (pointerY < top + EDGE_PX) dy = -Math.ceil(((top + EDGE_PX - pointerY) / EDGE_PX) * MAX_SCROLL_PER_FRAME)
      else if (pointerY > bottom - EDGE_PX) dy = Math.ceil(((pointerY - (bottom - EDGE_PX)) / EDGE_PX) * MAX_SCROLL_PER_FRAME)
      if (dy) {
        const before = scroller.scrollTop
        scroller.scrollTop += dy
        if (scroller.scrollTop !== before) frame = requestAnimationFrame(tick)
      }
    }

    const heldTop = pointerY - grabOffset
    const heldBottom = heldTop + rowEl.offsetHeight
    const all = rows()
    const above = all[index - 1]
    const below = all[index + 1]
    if (above && heldTop < layoutTop(above) + above.offsetHeight / 2 - HYSTERESIS_PX) {
      animatedMove(index, index - 1, rowEl)
      dragging.value = index - 1
    } else if (below && heldBottom > layoutTop(below) + below.offsetHeight / 2 + HYSTERESIS_PX) {
      animatedMove(index, index + 1, rowEl)
      dragging.value = index + 1
    }

    // Wherever its slot is now, draw the held row under the pointer.
    rowEl.style.transform = `translateY(${pointerY - grabOffset - layoutTop(rowEl)}px)`
  }

  function schedule() {
    if (!frame) frame = requestAnimationFrame(tick)
  }

  function begin(index: number) {
    rowEl = rows()[index] ?? null
    if (!rowEl) return
    dragging.value = index
    grabOffset = startY - layoutTop(rowEl)
    rowEl.style.transition = 'none'
    document.body.style.userSelect = 'none'
    schedule()
  }

  function onMove(e: PointerEvent) {
    if (e.pointerId !== pointerId) return
    pointerY = e.clientY
    if (pending && Math.abs(pointerY - startY) >= START_THRESHOLD_PX) {
      const { index } = pending
      pending = null
      begin(index)
    }
    if (dragging.value !== null) {
      e.preventDefault()
      schedule()
    }
  }

  function onUp(e: PointerEvent) {
    if (e.pointerId !== pointerId) return
    const el = rowEl
    const wasDragging = dragging.value !== null
    cleanup()
    if (!wasDragging || !el) return
    // Ease the row from under the pointer into its slot.
    el.style.transition = `transform ${DROP_MS}ms cubic-bezier(0.2, 0, 0, 1)`
    el.style.transform = ''
    clearTransitionLater(el, DROP_MS)
    // A drag is not a click on the row.
    window.addEventListener('click', swallowClick, { capture: true, once: true })
    setTimeout(() => window.removeEventListener('click', swallowClick, { capture: true }), 0)
  }

  function swallowClick(e: MouseEvent) {
    e.stopPropagation()
    e.preventDefault()
  }

  function cleanup() {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
    window.removeEventListener('pointercancel', onUp)
    if (frame) cancelAnimationFrame(frame)
    frame = 0
    pointerId = null
    pending = null
    dragging.value = null
    rowEl = null
    document.body.style.userSelect = ''
  }

  function listen(e: PointerEvent) {
    pointerId = e.pointerId
    startY = pointerY = e.clientY
    window.addEventListener('pointermove', onMove, { passive: false })
    window.addEventListener('pointerup', onUp)
    window.addEventListener('pointercancel', onUp)
  }

  /** On the row. Mouse only; interactive children keep their own clicks. */
  function onRowPointerDown(e: PointerEvent, index: number) {
    if (e.pointerType !== 'mouse' || e.button !== 0 || pointerId !== null) return
    const target = e.target as HTMLElement
    if (target.closest('button, a, input, select, textarea, label, [role="menu"], [role="menuitem"], [data-no-drag]')) return
    pending = { index }
    listen(e)
  }

  /** On the handle. Every pointer type; a finger starts dragging at once. */
  function onHandlePointerDown(e: PointerEvent, index: number) {
    if (e.button !== 0 || pointerId !== null) return
    e.preventDefault()
    listen(e)
    begin(index)
  }

  /** ↑/↓ on the focused handle move the row one place; focus stays with it. */
  function onHandleKeydown(e: KeyboardEvent, index: number) {
    const to = e.key === 'ArrowUp' ? index - 1 : e.key === 'ArrowDown' ? index + 1 : null
    if (to === null || to < 0 || to >= rows().length) return
    e.preventDefault()
    const handle = e.currentTarget as HTMLElement
    animatedMove(index, to, null)
    void nextTick(() => handle.focus())
  }

  onBeforeUnmount(cleanup)

  return { dragging, onRowPointerDown, onHandlePointerDown, onHandleKeydown }
}
