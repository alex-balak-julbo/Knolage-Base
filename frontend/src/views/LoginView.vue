<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ApiError } from '../api/client'
import { t } from '../i18n'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  busy.value = true
  error.value = ''
  try {
    await auth.login(email.value.trim(), password.value)
    const target = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') ? route.query.redirect : '/'
    await router.replace(target)
  } catch (e) {
    error.value = e instanceof ApiError && e.status === 429 ? t('login.tooMany') : e instanceof ApiError && e.status === 401 ? t('login.bad') : t('toast.error')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main class="flex min-h-dvh items-center justify-center bg-canvas p-4 text-ink">
    <form class="flex w-full max-w-sm flex-col gap-3 rounded-2xl border border-line bg-panel p-6 shadow-sm" @submit.prevent="submit">
      <h1 class="text-xl font-bold">📚 {{ t('app.title') }}</h1>
      <h2 class="text-sm text-muted">{{ t('login.title') }}</h2>
      <label class="flex flex-col gap-1 text-sm">
        {{ t('login.email') }}
        <input v-model="email" type="email" class="input" autocomplete="username" required autofocus />
      </label>
      <label class="flex flex-col gap-1 text-sm">
        {{ t('login.password') }}
        <input v-model="password" type="password" class="input" autocomplete="current-password" required />
      </label>
      <p v-if="error" class="text-sm text-danger" role="alert">{{ error }}</p>
      <button type="submit" class="btn-primary" :disabled="busy">{{ t('login.submit') }}</button>
    </form>
  </main>
</template>
