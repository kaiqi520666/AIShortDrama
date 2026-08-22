import { defineStore } from 'pinia'
import { changePassword as changePasswordRequest, getCurrentUser, login as loginRequest, logout as logoutRequest, register as registerRequest } from '../api/auth'
import { getCredits } from '../api/credits'
import { useModelCapabilitiesStore } from './modelCapabilities'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    initialized: false,
    creditPrices: [],
  }),
  actions: {
    setUser(user) {
      this.user = user
    },
    clear() {
      this.user = null
      this.creditPrices = []
      useModelCapabilitiesStore().clear()
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
    async changePassword(payload) {
      const result = await changePasswordRequest(payload)
      if (result.code !== 0) throw new Error(result.message)
      this.user = result.data
    },
    async refreshCredits() {
      if (!this.user) return
      const result = await getCredits()
      if (result.code !== 0) throw new Error(result.message)
      Object.assign(this.user, {
        credit_balance: result.data.balance,
        credit_frozen: result.data.frozen,
      })
      this.creditPrices = result.data.prices
    },
    estimateCredits(mediaType, model, { resolution = '', duration = 1 } = {}) {
      const rule = this.creditPrices.find((item) => item.media_type === mediaType && item.model === model && item.specification === (['image', 'video'].includes(mediaType) ? resolution : ''))
      if (!rule) return null
      if (mediaType === 'audio') return rule.freeze_credits
      return rule.unit_credits * (mediaType === 'video' ? duration : 1)
    },
  },
})
