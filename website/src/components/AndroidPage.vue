<script setup lang="ts">
/**
 * The /android page: where "Download for Android" leads, rather than a file arriving straight
 * away. Laid out the way download pages usually are: the app's tile, one big button for the
 * current build with its version, size and date under it, three short facts, the install in three
 * steps, and every version below for anyone who needs an older one.
 *
 * The list comes from the API's public versions.json. Until it answers (or if it can't), the
 * button still works: it points at /player/download, which always serves the current build.
 */
import { computed, onMounted, ref, watchEffect } from 'vue'
import IconAndroid from '~icons/material-symbols/android'
import IconArrow from '~icons/material-symbols/arrow-outward'
import IconDownload from '~icons/material-symbols/download'

import mark from '@/assets/marien-mark.png'
import { track } from '@/composables/useAnalytics'
import { useI18n } from '@/i18n'

const API = 'https://api.marien.co.id'
const DOCS = 'https://docs.marien.co.id'

interface Release { version: string; published_at: string; size_bytes: number; is_current: boolean; download_url: string }

const { m, locale } = useI18n()
const a = computed(() => m.value.android)
watchEffect(() => { document.title = a.value.metaTitle })

const releases = ref<Release[] | null>(null)
const failed = ref(false)
onMounted(async () => {
  try {
    const r = await fetch(`${API}/player/versions.json`)
    if (!r.ok) throw new Error(String(r.status))
    releases.value = await r.json()
  } catch {
    failed.value = true
  }
})
const current = computed(() => releases.value?.find((r) => r.is_current) ?? null)

const size = (b: number) => `${(b / 1_048_576).toFixed(1)} MB`
const date = (iso: string) =>
  new Date(iso).toLocaleDateString(locale.value === 'id' ? 'id-ID' : 'en-GB', { day: 'numeric', month: 'short', year: 'numeric' })

const STATEMENT = 'text-[2.125rem] leading-[1.1] sm:text-5xl lg:text-6xl lg:leading-[1.05]'
const GRADIENT = 'bg-gradient-to-r from-brand-strong to-brand-bright bg-clip-text text-transparent'
</script>

<template>
  <div class="mx-auto max-w-5xl px-5 pb-10 pt-28 sm:px-8 sm:pt-36">
    <!-- The app, and the one button. -->
    <section class="reveal flex flex-col items-center text-center">
      <span class="relative flex size-20 items-center justify-center rounded-[1.4rem] bg-white shadow-[0_20px_40px_-20px_rgba(0,24,77,0.45)] ring-1 ring-line">
        <img :src="mark" alt="" class="size-11" />
        <span class="absolute -bottom-2 -right-2 flex size-8 items-center justify-center rounded-full bg-white text-[#3ddc84] shadow ring-1 ring-line" aria-hidden="true">
          <IconAndroid class="size-5" />
        </span>
      </span>
      <p class="mt-6 text-xs font-semibold uppercase tracking-wider text-ink-subtle">{{ a.eyebrow }}</p>
      <h1 class="mt-3 max-w-3xl" :class="STATEMENT">{{ a.lead }} <span :class="GRADIENT">{{ a.rest }}</span></h1>
      <p class="mt-5 max-w-xl leading-relaxed text-ink-muted">{{ a.sub }}</p>

      <div class="mt-9 flex flex-col items-center gap-3 sm:flex-row">
        <a
          :href="current ? API + current.download_url : `${API}/player/download`"
          class="inline-flex items-center gap-2 rounded-lg bg-action px-7 py-4 text-base font-medium text-white transition-colors hover:bg-action-hover"
          @click="track('download_android', { location: 'android_page', version: current?.version ?? 'latest' })"
        >
          <IconDownload class="size-5" aria-hidden="true" />
          {{ current ? `${a.download} ${current.version}` : a.downloadLatest }}
        </a>
        <a :href="`${DOCS}/setting-up-your-device/#android-player`" target="_blank" rel="noopener" class="inline-flex items-center gap-1.5 rounded-lg px-5 py-4 text-sm font-medium text-ink ring-1 ring-ink/70 transition-colors hover:bg-ink hover:text-white">
          {{ a.guide }}<IconArrow class="size-4" aria-hidden="true" />
        </a>
      </div>
      <p class="mt-4 min-h-5 text-sm text-ink-subtle">
        <template v-if="current">APK · {{ size(current.size_bytes) }} · {{ date(current.published_at) }}</template>
      </p>
    </section>

    <!-- Three facts. -->
    <ul class="reveal mt-16 grid gap-4 sm:mt-20 sm:grid-cols-3 sm:gap-6">
      <li v-for="f in a.facts" :key="f.title" class="rounded-2xl bg-brand-soft p-6 ring-1 ring-tint-strong/60">
        <p class="display text-xl leading-snug text-ink">{{ f.title }}</p>
        <p class="mt-2 text-sm leading-relaxed text-ink-muted">{{ f.text }}</p>
      </li>
    </ul>

    <!-- The install, then every version. -->
    <div class="reveal mt-16 grid gap-10 sm:mt-20 lg:grid-cols-[0.9fr_1.1fr] lg:gap-14">
      <section>
        <h2 class="text-2xl leading-[1.15] sm:text-3xl">{{ a.stepsTitle }}</h2>
        <ol class="mt-6 space-y-5">
          <li v-for="(s, i) in a.steps" :key="i" class="flex gap-4">
            <span class="display flex size-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-strong to-brand-bright text-white">{{ i + 1 }}</span>
            <p class="pt-1 leading-relaxed text-ink-muted">{{ s }}</p>
          </li>
        </ol>
        <a :href="`${DOCS}/connecting-a-screen/`" target="_blank" rel="noopener" class="mt-6 inline-flex items-center gap-1.5 text-sm font-medium text-brand transition-colors hover:text-brand-strong">
          {{ a.connectGuide }}<IconArrow class="size-4" aria-hidden="true" />
        </a>
      </section>

      <section>
        <h2 class="text-2xl leading-[1.15] sm:text-3xl">{{ a.versionsTitle }}</h2>
        <div class="mt-6 overflow-hidden rounded-2xl bg-white ring-1 ring-line">
          <p v-if="!releases && !failed" class="px-5 py-6 text-sm text-ink-muted">{{ a.loading }}</p>
          <p v-else-if="failed" class="px-5 py-6 text-sm text-ink-muted">{{ a.failed }}</p>
          <table v-else class="w-full text-left text-sm">
            <thead class="border-b border-line text-xs uppercase tracking-wider text-ink-subtle">
              <tr>
                <th class="px-5 py-3 font-semibold">{{ a.version }}</th>
                <th class="px-2 py-3 font-semibold">{{ a.released }}</th>
                <th class="hidden px-2 py-3 font-semibold sm:table-cell">{{ a.size }}</th>
                <th class="px-5 py-3" />
              </tr>
            </thead>
            <tbody class="divide-y divide-line">
              <tr v-for="r in releases" :key="r.version">
                <td class="px-5 py-3.5 font-medium text-ink">
                  {{ r.version }}
                  <span v-if="r.is_current" class="ml-2 rounded-full bg-brand-soft px-2 py-0.5 text-xs font-medium text-brand">{{ a.latest }}</span>
                </td>
                <td class="whitespace-nowrap px-2 py-3.5 text-ink-muted">{{ date(r.published_at) }}</td>
                <td class="hidden px-2 py-3.5 text-ink-muted sm:table-cell">{{ size(r.size_bytes) }}</td>
                <td class="px-5 py-3.5 text-right">
                  <a
                    :href="API + r.download_url" class="inline-flex items-center gap-1 font-medium text-brand transition-colors hover:text-brand-strong"
                    @click="track('download_android', { location: 'android_versions', version: r.version })"
                  ><IconDownload class="size-4" aria-hidden="true" />{{ a.download }}</a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>
