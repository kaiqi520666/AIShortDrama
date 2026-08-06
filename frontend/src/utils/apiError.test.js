import { describe, expect, it } from 'vitest'
import { getApiErrorMessage } from './apiError'

describe('getApiErrorMessage', () => {
  it('prefers the API envelope message for non-2xx responses', () => {
    expect(getApiErrorMessage({ response: { data: { message: '工作台不存在' } } }, '加载失败')).toBe('工作台不存在')
  })

  it('uses the legacy envelope error message', () => {
    expect(getApiErrorMessage(new Error('上传失败'), '加载失败')).toBe('上传失败')
  })

  it('falls back when no usable error message exists', () => {
    expect(getApiErrorMessage({ response: { data: {} } }, '加载失败')).toBe('加载失败')
  })
})
