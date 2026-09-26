<script setup lang="ts">
import { useReveal } from '@/composables/useReveal'
import { page } from '@/composables/usePage'
import DemoPage from '@/components/DemoPage.vue'
import FeaturesPage from '@/components/FeaturesPage.vue'
import SoftwarePage from '@/components/SoftwarePage.vue'
import SiteDemoVideo from '@/components/SiteDemoVideo.vue'
import SiteFeatures from '@/components/SiteFeatures.vue'
import SiteFooter from '@/components/SiteFooter.vue'
import SiteHero from '@/components/SiteHero.vue'
import SiteNav from '@/components/SiteNav.vue'
import SiteResponsive from '@/components/SiteResponsive.vue'
import SiteVenues from '@/components/SiteVenues.vue'
import SiteConsent from '@/components/SiteConsent.vue'

useReveal()
</script>

<template>
  <SiteNav />
  <main>
    <DemoPage v-if="page === 'demo'" />
    <FeaturesPage v-else-if="page === 'features'" />
    <SoftwarePage v-else-if="page === 'software'" />
    <template v-else>
      <SiteHero />
      <SiteVenues />
      <SiteFeatures />
      <SiteResponsive />
      <SiteDemoVideo />
    </template>
  </main>
  <SiteFooter />
  <SiteConsent />
</template>
