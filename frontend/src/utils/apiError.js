export function getApiErrorMessage(error, fallback = '请求失败') {
  const message = error?.response?.data?.message || error?.message
  return typeof message === 'string' && message.trim() ? message : fallback
}
