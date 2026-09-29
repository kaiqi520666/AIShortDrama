import { afterEach, describe, expect, it } from 'vitest'
import { createApiError, getApiErrorMessage } from './apiError'
import { i18n } from '../i18n'

afterEach(() => { i18n.global.locale.value = 'id' })

describe('getApiErrorMessage', () => {
  it('does not display untranslated legacy API messages', () => {
    expect(getApiErrorMessage({ response: { status: 404, data: { message: '工作台不存在' } } })).toBe(i18n.global.t('errors.not_found'))
  })

  it('uses the legacy envelope error message', () => {
    expect(getApiErrorMessage(new Error('上传失败'), '加载失败')).toBe('上传失败')
  })

  it('falls back when no usable error message exists', () => {
    expect(getApiErrorMessage({ response: { data: {} } }, '加载失败')).toBe(i18n.global.t('errors.request_failed'))
    expect(getApiErrorMessage({}, '加载失败')).toBe('加载失败')
  })

  it('translates structured errors and interpolation in the current locale', () => {
    const payload = { code: 1, message: '原始错误', error_key: 'file_size_limit', error_params: { limit: '20MB' } }
    const error = createApiError(payload, 422)
    expect(error.message).toBe('Ukuran file tidak boleh melebihi 20MB.')
    i18n.global.locale.value = 'zh-CN'
    expect(error.message).toBe('文件不能超过 20MB。')
    expect(error.response.data).toBe(payload)
    expect(payload.message).toBe('原始错误')
  })

  it('uses safe fallbacks for unknown keys and gateway errors', () => {
    expect(getApiErrorMessage(createApiError({ error_key: 'future_error', message: '敏感错误' }, 502))).toBe(i18n.global.t('errors.upstream_unavailable'))
    expect(createApiError('<html>gateway error</html>', 503).message).toBe(i18n.global.t('errors.service_unavailable'))
    expect(getApiErrorMessage({ code: 1, message: '中文原文' })).toBe(i18n.global.t('errors.request_failed'))
  })

  it('localizes network and timeout failures without swallowing cancellation', () => {
    expect(getApiErrorMessage({ code: 'ERR_NETWORK', message: 'Network Error' })).toBe(i18n.global.t('errors.network_error'))
    expect(getApiErrorMessage({ code: 'ECONNABORTED' })).toBe(i18n.global.t('errors.request_timeout'))
    expect(getApiErrorMessage({ code: 'ERR_CANCELED', message: 'cancelled' })).toBe('cancelled')
  })
})
