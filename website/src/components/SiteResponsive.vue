<script setup lang="ts">
/**
 * The CMS on every size of screen a person might run it from: a monitor with the real
 * dashboard, and a tablet and a phone with the same overview laid out for them. The one blue
 * card on the page, so it lands as a change of pace.
 */
import MiniCms from './MiniCms.vue'
import { useI18n } from '@/i18n'

const { m } = useI18n()
</script>

<template>
  <section id="responsive" class="mx-auto max-w-7xl px-5 pt-16 sm:px-8 sm:pt-20">
    <div
      class="brand-sweep reveal relative overflow-hidden rounded-[2rem] px-5 pt-12 text-white sm:rounded-[2.5rem] sm:px-10 sm:pt-14"
    >
      <!-- Faint rings behind the devices, echoing the hero's dome. -->
      <div class="pointer-events-none absolute -bottom-[30rem] hidden sm:block left-1/2 size-[60rem] -translate-x-1/2 rounded-full border border-white/10" aria-hidden="true" />
      <div class="pointer-events-none absolute -bottom-[22rem] hidden sm:block left-1/2 size-[44rem] -translate-x-1/2 rounded-full border border-white/10" aria-hidden="true" />

      <div class="relative mx-auto max-w-3xl text-center">
        <h2 class="text-3xl leading-[1.15] sm:text-5xl sm:leading-[1.1]">
          {{ m.responsive.lead }} <span class="text-white/60">{{ m.responsive.rest }}</span>
        </h2>
      </div>

      <!-- The devices. Positions are percentages of the stage, so the group keeps its shape at
           every width, and the window over it shows only their top halves, running off the
           card's foot, so the card stays short. -->
      <div class="relative mx-auto mt-10 aspect-[16/4.2] max-w-5xl overflow-hidden sm:mt-12">
        <div class="absolute inset-x-0 top-0 aspect-[16/9.4]">
          <!-- Monitor. -->
          <div class="absolute left-[15%] top-0 w-[70%]">
            <div class="rounded-[1.4%/2.2%] bg-[#0b0e14] p-[1.1%] shadow-[0_40px_100px_-30px_rgba(0,0,0,0.7)] ring-1 ring-white/15">
              <img src="/shots/overview.webp" :alt="m.responsive.monitorAlt" class="block aspect-[16/10] w-full rounded-[0.6%/1%] object-cover object-left-top" loading="lazy" decoding="async" />
            </div>
            <div class="mx-auto h-[1.8vw] max-h-6 w-[14%] bg-gradient-to-b from-[#2a2f3a] to-[#171b23]" aria-hidden="true" />
            <div class="mx-auto h-[0.7vw] max-h-2.5 w-[34%] rounded-t-md bg-[#2a2f3a]" aria-hidden="true" />
          </div>

          <!-- Tablet. -->
          <div class="float absolute left-0 top-[20%] w-[27%]" style="--float-delay: -2s">
            <div class="rounded-[9%/7%] bg-[#0b0e14] p-[3.5%] shadow-[0_30px_80px_-24px_rgba(0,0,0,0.75)] ring-1 ring-white/20">
              <div class="aspect-[3/4] overflow-hidden rounded-[5%/4%]">
                <MiniCms size="tablet" />
              </div>
            </div>
          </div>

          <!-- Phone. -->
          <div class="float absolute right-[5%] top-[26%] w-[15%]" style="--float-delay: -4s">
            <div class="rounded-[18%/8.5%] bg-[#0b0e14] p-[5%] shadow-[0_30px_80px_-24px_rgba(0,0,0,0.75)] ring-1 ring-white/20">
              <div class="aspect-[9/19.5] overflow-hidden rounded-[13%/6%]">
                <MiniCms size="phone" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
