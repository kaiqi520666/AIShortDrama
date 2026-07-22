import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import './style.css'

const pinia = createPinia()

createApp(App).use(pinia).mount('#app')
