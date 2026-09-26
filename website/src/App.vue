<script setup lang="ts">
import { useReveal } from '@/composables/useReveal'
import { page } from '@/composables/usePage'
import DemoPage from '@/components/DemoPage.vue'
import FeaturesPage from '@/components/FeaturesPage.vue'
import SiteFaq from '@/components/SiteFaq.vue'
import SiteFeatures from '@/components/SiteFeatures.vue'
import SiteFooter from '@/components/SiteFooter.vue'
import SiteHero from '@/components/SiteHero.vue'
import SiteNav from '@/components/SiteNav.vue'
import SiteResponsive from '@/components/SiteResponsive.vue'
import SiteVenues from '@/components/SiteVenues.vue'

useReveal()
</script>

<template>
  <SiteNav />
  <main>
    <DemoPage v-if="page === 'demo'" />
    <FeaturesPage v-else-if="page === 'features'" />
    <template v-else>
      <SiteHero />
      <SiteVenues />
      <SiteFeatures />
      <SiteResponsive />
      <SiteFaq />
    </template>
  </main>
  <SiteFooter />
</template>
