import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { configure } from './api/client'
import App from './App.vue'
import { locale, setLocale } from './i18n'
import { router } from './router'
import { useAuthStore } from './stores/auth'
import { useUiStore } from './stores/ui'
import './style.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia).use(router)

configure({
  baseUrl: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  onAuthLost: () => {
    useAuthStore().lost()
    void router.push({ name: 'login', query: { redirect: router.currentRoute.value.fullPath } })
  },
})
setLocale(locale.value)
useUiStore().initTheme()
app.mount('#app')
