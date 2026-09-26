<script setup lang="ts">
/** Publishing, as one of the feature cards: the title and a line, and the animated scene. */
import FeatureCard from './FeatureCard.vue'
import PublishScene from './PublishScene.vue'
import { useI18n } from '@/i18n'

const { m } = useI18n()
</script>

<template>
  <section id="publish">
    <FeatureCard>
      <template #visual>
        <PublishScene class="-ml-6 sm:-ml-8 lg:-ml-10" />
      </template>

      <h3 class="text-xl leading-[1.2] sm:text-4xl sm:leading-[1.1]">{{ m.publish.title }}</h3>
      <p class="mt-3 max-w-md leading-relaxed text-ink-muted">{{ m.publish.body }}</p>
    </FeatureCard>
  </section>
</template>
