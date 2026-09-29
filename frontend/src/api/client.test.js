import { afterEach, describe, expect, it, vi } from 'vitest'
import { AxiosError } from 'axios'
import { apiClient, setupAuthInterceptor } from './client'
import { i18n } from '../i18n'
import { getApiErrorMessage } from '../utils/apiError'

const handlers = []
afterEach(() => {
  handlers.forEach((id) => apiClient.interceptors.response.eject(id))
  handlers.length = 0
  i18n.global.locale.value = 'id'
})

describe('API error transport', () => {
  it('rejects HTTP-200 failure envelopes without losing structured fields', async () => {
    const data = { code: 1, message: '余额不足', data: { balance: 2 }, error_key: 'insufficient_credits' }
    const error = await apiClient.get('/test', {
      adapter: async (config) => ({ data, status: 200, config }),
    }).catch((error) => error)
    expect(error.response.data).toBe(data)
    expect(error.message).toBe(i18n.global.t('errors.insufficient_credits'))
    i18n.global.locale.value = 'zh-CN'
    expect(getApiErrorMessage(error)).toBe(i18n.global.t('errors.insufficient_credits'))
  })

  it('keeps HTTP status and error data used by login security', async () => {
    const data = { code: 1, message: '登录错误', error_key: 'invalid_credentials', data: { captcha_required: true } }
    const error = await apiClient.get('/auth/login', {
      adapter: async (config) => { throw new AxiosError('raw', 'ERR_BAD_REQUEST', config, null, { status: 401, data }) },
    }).catch((error) => error)
    expect(error.response.status).toBe(401)
    expect(error.response.data.data.captcha_required).toBe(true)
    expect(error.message).toBe(i18n.global.t('errors.invalid_credentials'))
  })

  it('still refreshes once and retries the original request', async () => {
    const auth = { setUser: vi.fn(), clear: vi.fn() }
    const router = { currentRoute: { value: { meta: {} } }, replace: vi.fn() }
    const id = apiClient.interceptors.response.handlers.length
    setupAuthInterceptor(auth, router)
    handlers.push(id)
    const previousAdapter = apiClient.defaults.adapter
    const user = { id: 'test-user' }
    const adapter = vi.fn(async (config) => {
      if (config.url === '/auth/refresh') return { status: 200, data: { code: 0, data: user }, config }
      if (!config._retried) throw new AxiosError('raw', 'ERR_BAD_REQUEST', config, null, { status: 401, data: { error_key: 'unauthorized' } })
      return { status: 200, data: { code: 0, data: 'ok' }, config }
    })
    apiClient.defaults.adapter = adapter
    try {
      expect((await apiClient.get('/test')).data.data).toBe('ok')
      expect(auth.setUser).toHaveBeenCalledWith(user)
      expect(auth.clear).not.toHaveBeenCalled()
      expect(adapter).toHaveBeenCalledTimes(3)
    } finally {
      apiClient.defaults.adapter = previousAdapter
    }
  })
})
