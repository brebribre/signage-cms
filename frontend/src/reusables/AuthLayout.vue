<script setup lang="ts">
/**
 * The shell every signed-out page sits in: sign in, reset password, and choosing your own
 * password for the first time.
 *
 * On a wide screen it is two columns. The left is the marketing site's blue card, brought into
 * the product: the brand sweep, the hairline grain over it, the wordmark in white and one line
 * about what this is. The right is the form, and nothing else — the panel is scenery, so it
 * carries no control a person could go looking for and fail to find on a phone.
 *
 * Below `lg` the panel is gone rather than stacked. A tall blue block above the form would push
 * the fields under the fold on a phone, which is the one place signing in has to be quick, so
 * the small screen keeps exactly the single centred column it had before.
 *
 * All three pages share it so moving between them (the Reset password link, most obviously) does
 * not jump between two different layouts.
 */
import AppLogo from '@/reusables/AppLogo.vue'
</script>

<template>
  <div class="min-h-full bg-canvas lg:grid lg:grid-cols-2">
    <!-- The hero. Decorative: it is hidden below `lg` and holds nothing to act on. -->
    <aside class="auth-hero relative hidden overflow-hidden lg:flex lg:flex-col lg:justify-between lg:p-12 xl:p-16">
      <!-- The same faint rings the site's blue card uses, anchored off the bottom corner so they
           read as one big arc rather than circles. -->
      <div
        class="pointer-events-none absolute -bottom-[28rem] -left-[10rem] size-[52rem] rounded-full border border-white/10"
        aria-hidden="true"
      />
      <div
        class="pointer-events-none absolute -bottom-[20rem] -left-[4rem] size-[38rem] rounded-full border border-white/10"
        aria-hidden="true"
      />

      <AppLogo class="relative self-start" tone="white" />

      <div class="relative max-w-md">
        <p class="font-display text-4xl leading-[1.15] tracking-heading text-white xl:text-5xl xl:leading-[1.1]">
          The smart way to run your screens.
        </p>
        <p class="mt-4 text-lg text-white/70">
          Pictures, videos and websites, on any display.
        </p>
      </div>
    </aside>

    <!-- The form. Centred in its own column on a wide screen, and the whole page below `lg`. -->
    <main class="flex min-h-full items-center justify-center px-4 py-12 sm:px-8">
      <div class="w-full max-w-sm">
        <!-- The wordmark rides above the form only where the panel is not showing it. -->
        <AppLogo class="mb-8 block lg:hidden" />
        <slot />
      </div>
    </main>
  </div>
</template>
