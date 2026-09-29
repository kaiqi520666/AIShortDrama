import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { i18n, initializeLocale } from './i18n'
import { setupAuthInterceptor } from './api/client'
import { initializeTheme } from './composables/useTheme'
import { createAppRouter } from './router'
import { useAuthStore } from './stores/auth'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import './styles/index.css'

initializeLocale()
initializeTheme()
const pinia = createPinia()
const authStore = useAuthStore(pinia)
const router = createAppRouter(authStore)
setupAuthInterceptor(authStore, router)

createApp(App).use(pinia).use(router).use(i18n).mount('#app')
