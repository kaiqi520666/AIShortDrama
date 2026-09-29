import axios from 'axios'
import { createApiError, getApiErrorMessage } from '../utils/apiError'

export const apiClient = axios.create({ baseURL: '/api', withCredentials: true })

apiClient.interceptors.response.use(
  (response) => {
    if (response.data?.code === 1) throw createApiError(response.data, response.status)
    return response
  },
  (error) => {
    if (error.response || ['ERR_NETWORK', 'ECONNABORTED', 'ETIMEDOUT'].includes(error.code)) {
      const message = getApiErrorMessage(error)
      error.message = message
    }
    return Promise.reject(error)
  },
)

let refreshPromise = null

export function setupAuthInterceptor(authStore, router) {
  apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
      const request = error.config
      const authRequest = /^\/auth\/(login|register|refresh)$/.test(request?.url || '')
      if (error.response?.status !== 401 || request?._retried || authRequest) throw error

      request._retried = true
      refreshPromise ||= apiClient.post('/auth/refresh')
        .then(({ data }) => authStore.setUser(data.data))
        .finally(() => { refreshPromise = null })

      try {
        await refreshPromise
        return apiClient(request)
      } catch (refreshError) {
        authStore.clear()
        const route = router.currentRoute.value
        if (route.meta.requiresAuth) {
          await router.replace({ name: 'login', query: { redirect: route.fullPath } })
        }
        throw refreshError
      }
    },
  )
}
