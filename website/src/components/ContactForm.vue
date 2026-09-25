<script setup lang="ts">
/**
 * The Request access form, in the closing card. It posts straight into the Paskall: Request
 * access Google Form (owned by the Paskall Google account), so every request lands in that form's
 * Responses tab with no server of ours in between.
 *
 * Google answers a post from another site without letting the page read the reply, so the form
 * checks everything itself first: a name, and an email or a phone number (at least one). The
 * Google Form marks only the name required, so a post that passes here is never turned away there.
 */
import { computed, reactive, ref } from 'vue'
import IconArrowForward from '~icons/material-symbols/arrow-forward'
import IconCheck from '~icons/material-symbols/check-circle'

import { useI18n } from '@/i18n'

const FORM_URL = 'https://docs.google.com/forms/d/e/1FAIpQLScmhLhdLNcrqJUUcCRAkl8SGuZ29MNOgb4r7hIrhfngu4Itmg/formResponse'
/** The Google Form's own id for each question. They change only if a question is deleted and
 *  made again, so edit a question's wording in Google Forms rather than replacing it. */
const ENTRY = { name: 'entry.908758721', company: 'entry.283883140', email: 'entry.645715297', phone: 'entry.1295450662' }

const { m } = useI18n()
const f = computed(() => m.value.footer.form)

const values = reactive({ name: '', company: '', email: '', phone: '' })
/** Left empty by people; a bot filling every field fills it too, and its post is dropped. */
const trap = ref('')
const state = ref<'idle' | 'sending' | 'sent' | 'failed'>('idle')
const tried = ref(false)

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
/** Digits, spaces, dashes, dots, brackets and a leading +, with at least 8 digits in all. */
const phoneOk = (v: string) => /^\+?[\d\s().-]+$/.test(v) && v.replace(/\D/g, '').length >= 8

const errors = computed(() => {
  const email = values.email.trim()
  const phone = values.phone.trim()
  return {
    name: values.name.trim() ? '' : f.value.errors.name,
    contact: email || phone ? '' : f.value.errors.contact,
    email: email && !EMAIL.test(email) ? f.value.errors.email : '',
    phone: phone && !phoneOk(phone) ? f.value.errors.phone : '',
  }
})
const valid = computed(() => Object.values(errors.value).every((e) => !e))

async function submit() {
  tried.value = true
  if (!valid.value || state.value === 'sending') return
  if (trap.value) { state.value = 'sent'; return }
  state.value = 'sending'
  const body = new URLSearchParams()
  for (const key of Object.keys(ENTRY) as (keyof typeof ENTRY)[]) body.set(ENTRY[key], values[key].trim())
  try {
    // no-cors: the post goes through, but the reply can't be read, so only a network failure
    // (offline, blocked) shows up here.
    await fetch(FORM_URL, { method: 'POST', mode: 'no-cors', body })
    state.value = 'sent'
  } catch {
    state.value = 'failed'
  }
}

const field = 'mt-1.5 block w-full rounded-lg bg-white px-4 py-3 text-base text-ink ring-1 ring-line outline-none transition-shadow placeholder:text-ink-subtle focus:ring-2 focus:ring-brand'
</script>

<template>
  <div class="relative mx-auto mt-10 max-w-xl text-left">
    <div v-if="state === 'sent'" class="rounded-xl bg-white/80 px-6 py-10 text-center ring-1 ring-line backdrop-blur" role="status">
      <IconCheck class="mx-auto size-10 text-emerald-600" />
      <p class="display mt-4 text-2xl text-ink">{{ f.sentTitle }}</p>
      <p class="mt-2 text-ink-muted">{{ f.sentBody }}</p>
    </div>

    <form v-else class="rounded-xl bg-white/70 p-5 ring-1 ring-line backdrop-blur sm:p-8" novalidate @submit.prevent="submit">
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="block sm:col-span-2">
          <span class="text-sm font-medium text-ink">{{ f.name }}</span>
          <input v-model="values.name" :class="field" type="text" name="name" autocomplete="name" :aria-invalid="tried && !!errors.name" />
          <span v-if="tried && errors.name" class="mt-1 block text-sm text-red-600">{{ errors.name }}</span>
        </label>
        <label class="block sm:col-span-2">
          <span class="text-sm font-medium text-ink">{{ f.company }} <span class="font-normal text-ink-subtle">{{ f.optional }}</span></span>
          <input v-model="values.company" :class="field" type="text" name="company" autocomplete="organization" />
        </label>
        <label class="block">
          <span class="text-sm font-medium text-ink">{{ f.email }}</span>
          <input v-model="values.email" :class="field" type="email" name="email" autocomplete="email" inputmode="email" :aria-invalid="tried && !!(errors.email || errors.contact)" />
          <span v-if="tried && errors.email" class="mt-1 block text-sm text-red-600">{{ errors.email }}</span>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-ink">{{ f.phone }}</span>
          <input v-model="values.phone" :class="field" type="tel" name="phone" autocomplete="tel" inputmode="tel" :aria-invalid="tried && !!(errors.phone || errors.contact)" />
          <span v-if="tried && errors.phone" class="mt-1 block text-sm text-red-600">{{ errors.phone }}</span>
        </label>
      </div>
      <p class="mt-3 text-sm" :class="tried && errors.contact ? 'text-red-600' : 'text-ink-muted'">
        {{ tried && errors.contact ? errors.contact : f.eitherHint }}
      </p>

      <!-- Off screen and out of the tab order: only a bot fills it. -->
      <input v-model="trap" type="text" name="website" tabindex="-1" autocomplete="off" aria-hidden="true" class="absolute -left-[9999px] h-px w-px opacity-0" />

      <button
        type="submit" :disabled="state === 'sending'"
        class="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-action px-6 py-4 text-base font-medium text-white transition-colors hover:bg-action-hover disabled:opacity-70"
      >
        {{ state === 'sending' ? f.sending : m.footer.cta }} <IconArrowForward v-if="state !== 'sending'" class="size-5" />
      </button>
      <p v-if="state === 'failed'" class="mt-3 text-center text-sm text-red-600" role="alert">{{ f.errors.send }}</p>
    </form>
  </div>
</template>
