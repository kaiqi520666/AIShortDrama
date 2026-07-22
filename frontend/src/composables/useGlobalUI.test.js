import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'
import { useGlobalConfirm, useGlobalToast } from './useGlobalUI'

beforeAll(() => {
  if (!globalThis.window) globalThis.window = globalThis
})

afterEach(() => vi.useRealTimers())

describe('global UI', () => {
  it('removes timed toasts', () => {
    vi.useFakeTimers()
    const toast = useGlobalToast()
    const id = toast.success('保存成功', 1000)

    expect(toast.toasts.value.some((item) => item.id === id)).toBe(true)
    vi.advanceTimersByTime(1000)
    expect(toast.toasts.value.some((item) => item.id === id)).toBe(false)
  })

  it('resolves confirm results', async () => {
    const dialog = useGlobalConfirm()
    const result = dialog.confirm({ title: '删除项目' })

    expect(dialog.confirmState.value.title).toBe('删除项目')
    dialog.acceptConfirm()
    await expect(result).resolves.toBe(true)
    expect(dialog.confirmState.value).toBeNull()
  })
})
