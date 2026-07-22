import axios from 'axios'

export const apiClient = axios.create({ baseURL: '/api', withCredentials: true })

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
