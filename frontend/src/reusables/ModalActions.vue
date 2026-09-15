<script setup lang="ts">
/**
 * A dialog's button row — Cancel, Save, Apply. Sticks to the bottom of the dialog's scrolling
 * body, so however tall the content gets (a long screen list, a phone in landscape), the way to
 * finish is always on screen. Works from inside a form or a child component too: sticky follows
 * the nearest scroller, which is AppModal's body.
 *
 * The negative margins cancel AppModal's body padding (px-5, and pb-5 plus the home-indicator
 * inset on a phone), so the bar's divider runs edge to edge and it sits flush with the dialog's
 * bottom — keeping that inset as its own padding, so the buttons clear the indicator. The sticky
 * offset is negative by the same amount: sticky measures from inside the scroller's padding, so
 * `bottom-0` would park the bar that far above the edge with content showing beneath it.
 */
</script>

<template>
  <div
    class="sticky -bottom-[calc(1.25rem_+_env(safe-area-inset-bottom))] z-10 -mx-5 mt-4
           -mb-[calc(1.25rem_+_env(safe-area-inset-bottom))] flex flex-wrap sm:-bottom-5
           items-center justify-end gap-2 border-t border-line bg-canvas px-5 pt-4
           pb-[calc(1rem_+_env(safe-area-inset-bottom))] sm:-mb-5 sm:pb-4"
  >
    <slot />
  </div>
</template>
