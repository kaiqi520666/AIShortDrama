import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { setupAuthInterceptor } from './api/client'
import { createAppRouter } from './router'
import { useAuthStore } from './stores/auth'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import './styles/index.css'

const pinia = createPinia()
const authStore = useAuthStore(pinia)
const router = createAppRouter(authStore)
setupAuthInterceptor(authStore, router)

createApp(App).use(pinia).use(router).mount('#app')
