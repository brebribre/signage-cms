import { ref, watch } from 'vue'

const STORAGE_KEY = 'sidebar-collapsed'

function read(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false // private window or blocked storage: open, the default
  }
}

/** Module state: one sidebar, and the page frame beside it reads the same value. */
const collapsed = ref(read())
watch(collapsed, (value) => {
  try {
    localStorage.setItem(STORAGE_KEY, value ? '1' : '0')
  } catch {
    /* not remembered — it still works for this visit */
  }
})

/** Whether the desktop sidebar is folded down to its icons. Remembered per browser: someone who
 *  wants the room wants it on every page and every visit. */
export function useSidebarCollapsed() {
  return { collapsed, toggle: () => (collapsed.value = !collapsed.value) }
}
