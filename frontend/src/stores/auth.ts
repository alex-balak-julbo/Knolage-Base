import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '../api/endpoints.ts'
import type { User } from '../api/types.ts'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const ready = ref(false)
  let initPromise: Promise<void> | null = null

  /** Restores the session from the HttpOnly refresh cookie (once per page load). */
  function init(): Promise<void> {
    initPromise ??= (async () => {
      const res = await authApi.refresh()
      user.value = res?.user ?? null
      ready.value = true
    })()
    return initPromise
  }

  async function login(email: string, password: string): Promise<void> {
    const res = await authApi.login(email, password)
    user.value = res.user
    ready.value = true
    initPromise = Promise.resolve()
  }

  async function logout(): Promise<void> {
    await authApi.logout()
    user.value = null
    initPromise = Promise.resolve()
  }

  /** Called by the API client when a refresh fails. */
  function lost(): void {
    user.value = null
    initPromise = Promise.resolve()
  }

  return { user, ready, init, login, logout, lost }
})
