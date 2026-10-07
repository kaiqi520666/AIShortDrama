import { i18n } from '../i18n/index'

const statusKeys = {
  400: 'invalid_request', 401: 'unauthorized', 402: 'insufficient_credits',
  403: 'forbidden', 404: 'not_found', 405: 'method_not_allowed',
  409: 'conflict', 413: 'file_too_large', 422: 'invalid_request',
  429: 'rate_limited', 502: 'upstream_unavailable', 503: 'service_unavailable', 504: 'task_timeout',
}

export function getApiErrorMessage(error, fallback) {
  const { t, te } = i18n.global
  const payload = error?.response?.data || error
  const key = payload?.error_key
  if (typeof key === 'string' && te(`errors.${key}`)) return t(`errors.${key}`, payload.error_params || {})
  if (error?.response || key || payload?.code === 1 || payload?.type === 'error') {
    const status = error?.response?.status
    return t(`errors.${statusKeys[status] || (status >= 500 ? 'service_unavailable' : 'request_failed')}`)
  }
  if (error?.code === 'ERR_NETWORK' || error?.code === 'ECONNABORTED' || error?.code === 'ETIMEDOUT') {
    return t(`errors.${error.code === 'ERR_NETWORK' ? 'network_error' : 'request_timeout'}`)
  }
  const message = error?.message
  fallback ||= t('errors.request_failed')
  return typeof message === 'string' && message.trim() ? message : fallback
}

export function createApiError(payload, status) {
  const error = new Error()
  error.response = { data: payload, status }
  Object.defineProperty(error, 'message', { configurable: true, get: () => getApiErrorMessage(error) })
  return error
}

export function getTaskErrorMessage(task) {
  return getApiErrorMessage({
    error_key: task.error_key || { failed: 'generation_failed', cancelled: 'task_cancelled', timeout: 'task_timeout', needs_review: 'task_needs_review' }[task.status] || 'generation_failed',
    error_params: task.error_params,
  })
}
