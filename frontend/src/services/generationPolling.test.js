import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { getGenerationTask } from '../api/generations'
import { startGenerationPolling, stopAllGenerationPolling, stopGenerationPolling, stopWorkspaceGenerationPolling } from './generationPolling'
import { i18n } from '../i18n'

vi.mock('../api/generations', () => ({ getGenerationTask: vi.fn() }))

beforeEach(() => {
  setActivePinia(createPinia())
  stopAllGenerationPolling()
  vi.clearAllMocks()
})

describe('generation polling', () => {
  it('writes a successful result and stops polling', async () => {
    getGenerationTask.mockResolvedValue({
      code: 0,
      data: { status: 'succeeded', progress: 100, task_type: 'image', result: { type: 'image', data: [{ url: 'https://cdn.test/image.png', asset_id: 'asset-1' }] } },
    })
    const update = vi.fn()

    startGenerationPolling('task-1', 'node-1', update, 'workspace-1')
    await vi.waitFor(() => expect(update).toHaveBeenCalledWith('node-1', expect.objectContaining({ asset: 'https://cdn.test/image.png', status: 'ready' })))
    expect(getGenerationTask).toHaveBeenCalledOnce()
  })

  it('stops immediately on a deterministic client error', async () => {
    getGenerationTask.mockRejectedValue({ response: { status: 404, data: { message: '任务不存在' } } })
    const update = vi.fn()

    startGenerationPolling('task-2', 'node-2', update, 'workspace-1')
    await vi.waitFor(() => expect(update).toHaveBeenCalledWith('node-2', expect.objectContaining({ status: 'failed', generationError: i18n.global.t('errors.not_found') })))
    expect(getGenerationTask).toHaveBeenCalledOnce()
  })

  it('cancels all polling when token refresh fails', async () => {
    vi.useFakeTimers()
    getGenerationTask.mockImplementation((taskId) => taskId === 'expired-task'
      ? Promise.reject({ response: { status: 401, data: { message: '登录状态已失效' } } })
      : Promise.resolve({ code: 0, data: { status: 'running', progress: 20 } }))
    const update = vi.fn()

    startGenerationPolling('expired-task', 'node-1', update, 'workspace-1')
    startGenerationPolling('other-task', 'node-2', update, 'workspace-2')
    await vi.waitFor(() => expect(update).toHaveBeenCalledWith('node-1', expect.objectContaining({ status: 'failed' })))
    await vi.runAllTimersAsync()

    expect(getGenerationTask).toHaveBeenCalledTimes(2)
    vi.useRealTimers()
  })

  it.each(['failed', 'cancelled', 'timeout'])('localizes %s without rewriting original task diagnostics', async (status) => {
    const task = { status, task_type: 'image', error_message: '第三方原始错误', result: null }
    getGenerationTask.mockResolvedValue({ code: 0, data: task })
    const update = vi.fn()
    startGenerationPolling(`task-${status}`, 'node-1', update, 'workspace-1')
    const key = { failed: 'generation_failed', cancelled: 'task_cancelled', timeout: 'task_timeout' }[status]
    await vi.waitFor(() => expect(update).toHaveBeenCalledWith('node-1', expect.objectContaining({ generationError: i18n.global.t(`errors.${key}`) })))
    expect(task.error_message).toBe('第三方原始错误')
    expect(task.result).toBeNull()
  })

  it('backs off and pauses after six transient failures', async () => {
    vi.useFakeTimers()
    getGenerationTask.mockRejectedValue(new Error('offline'))
    const update = vi.fn()

    startGenerationPolling('task-3', 'node-3', update, 'workspace-1')
    await vi.runAllTimersAsync()

    expect(getGenerationTask).toHaveBeenCalledTimes(6)
    expect(update).toHaveBeenCalledWith('node-3', expect.objectContaining({ generationPollingPaused: true }))
    vi.useRealTimers()
  })

  it('cancels scheduled polling explicitly', async () => {
    vi.useFakeTimers()
    getGenerationTask.mockResolvedValue({ code: 0, data: { status: 'running', progress: 20 } })

    startGenerationPolling('task-4', 'node-4', vi.fn(), 'workspace-1')
    await Promise.resolve()
    stopGenerationPolling('task-4')
    await vi.runAllTimersAsync()

    expect(getGenerationTask).toHaveBeenCalledOnce()
    vi.useRealTimers()
  })

  it('ignores an in-flight response after cancellation', async () => {
    let resolveTask
    getGenerationTask.mockReturnValue(new Promise((resolve) => { resolveTask = resolve }))
    const update = vi.fn()

    startGenerationPolling('in-flight-task', 'node-4', update, 'workspace-1')
    stopGenerationPolling('in-flight-task')
    resolveTask({ code: 0, data: { status: 'running', progress: 30 } })
    await Promise.resolve()
    await Promise.resolve()

    expect(update).not.toHaveBeenCalled()
  })

  it('only cancels polling for the workspace being closed', async () => {
    vi.useFakeTimers()
    getGenerationTask.mockResolvedValue({ code: 0, data: { status: 'running', progress: 20 } })

    startGenerationPolling('task-5', 'node-5', vi.fn(), 'workspace-1')
    startGenerationPolling('task-6', 'node-6', vi.fn(), 'workspace-2')
    await Promise.resolve()
    stopWorkspaceGenerationPolling('workspace-1')
    await vi.advanceTimersByTimeAsync(5000)

    expect(getGenerationTask).toHaveBeenCalledTimes(3)
    vi.useRealTimers()
  })

  it('cancels every active poll on logout', async () => {
    vi.useFakeTimers()
    getGenerationTask.mockResolvedValue({ code: 0, data: { status: 'running', progress: 20 } })

    startGenerationPolling('task-7', 'node-7', vi.fn(), 'workspace-1')
    startGenerationPolling('task-8', 'node-8', vi.fn(), 'workspace-2')
    await Promise.resolve()
    stopAllGenerationPolling()
    await vi.runAllTimersAsync()

    expect(getGenerationTask).toHaveBeenCalledTimes(2)
    vi.useRealTimers()
  })
})
