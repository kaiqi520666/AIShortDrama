import { afterEach, describe, expect, it } from 'vitest'
import { useGlobalLoading } from './useGlobalLoading'

const loading = useGlobalLoading()

afterEach(() => loading.clearLoading())

describe('global loading', () => {
  it('keeps the overlay visible until every task finishes', () => {
    const first = loading.showLoading('打开工作台')
    const second = loading.showLoading('加载资产')

    expect(loading.visible.value).toBe(true)
    expect(loading.message.value).toBe('加载资产')
    loading.hideLoading(first)
    expect(loading.visible.value).toBe(true)
    loading.hideLoading(second)
    expect(loading.visible.value).toBe(false)
  })
})
