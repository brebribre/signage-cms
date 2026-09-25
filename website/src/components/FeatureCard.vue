<script setup lang="ts">
/**
 * One of the feature cards: a white card with a hairline border, a small outlined tag, a heading
 * and the words on one side, and the thing itself on the other, standing on a sweep of the
 * brand blues and running off the card's outer and bottom edges, as if the card were a window
 * onto a bigger scene.
 *
 * `side` is where the picture sits on a wide page; the cards alternate so a run of them
 * zigzags. On a phone the picture is always under the words, running off the right and bottom.
 */
defineProps<{ tag: string; side: 'left' | 'right' }>()
</script>

<template>
  <div class="reveal relative overflow-hidden rounded-[2rem] bg-white ring-1 ring-line sm:rounded-[2.5rem]">
    <div class="grid grid-cols-1 lg:grid-cols-2">
      <div class="min-w-0 self-center p-6 pb-10 sm:p-10 sm:pb-12 lg:p-14" :class="side === 'left' && 'lg:order-last'">
        <span class="tag text-brand-deep">{{ tag }}</span>
        <slot />
      </div>
      <div class="@container relative min-w-0 self-end pl-6 sm:pl-10 lg:pl-0 lg:pt-14" :class="side === 'left' && 'lg:order-first'">
        <!-- The sweep, behind the picture. -->
        <div
          class="card-sweep pointer-events-none absolute top-[6%] h-[86%] rounded-[50%]"
          :class="side === 'left' ? '-left-[30%] -right-[10%] rotate-[28deg]' : '-left-[10%] -right-[30%] -rotate-[28deg]'"
          aria-hidden="true"
        />
        <div class="relative">
          <slot name="visual" />
        </div>
      </div>
    </div>
  </div>
</template>
