import { createApp } from 'vue'

import '@fontsource-variable/inter'
import '@fontsource-variable/outfit'
import './style.css'
import App from './App.vue'
import { initAnalytics } from './composables/useAnalytics'

initAnalytics()

createApp(App).mount('#app')
