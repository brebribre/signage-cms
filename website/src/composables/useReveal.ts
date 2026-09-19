import { onBeforeUnmount, onMounted } from 'vue'

/** Adds `is-in` to every `.reveal` element as it scrolls into view, once. */
export function useReveal() {
  let observer: IntersectionObserver | null = null
  onMounted(() => {
    observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add('is-in')
            observer?.unobserve(e.target)
          }
        }
      },
      { rootMargin: '0px 0px -10% 0px', threshold: 0.1 },
    )
    document.querySelectorAll('.reveal').forEach((el) => observer!.observe(el))
  })
  onBeforeUnmount(() => observer?.disconnect())
}
