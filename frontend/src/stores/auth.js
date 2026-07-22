import { defineStore } from 'pinia'
import { getCurrentUser, login as loginRequest, logout as logoutRequest, register as registerRequest } from '../api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    initialized: false,
  }),
  actions: {
    setUser(user) {
      this.user = user
    },
    clear() {
      this.user = null
    },
    async restore() {
      if (this.initialized) return
      try {
        const result = await getCurrentUser()
        if (result.code === 0) this.user = result.data
      } catch {
        this.user = null
      } finally {
        this.initialized = true
      }
    },
    async register(payload) {
      const result = await registerRequest(payload)
      if (result.code !== 0) throw new Error(result.message)
      this.user = result.data
    },
    async login(payload) {
      const result = await loginRequest(payload)
      if (result.code !== 0) throw new Error(result.message)
      this.user = result.data
    },
    async logout() {
      try {
        await logoutRequest()
      } finally {
        this.clear()
      }
    },
  },
})
