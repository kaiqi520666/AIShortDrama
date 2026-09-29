import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { useStreamingTextTask } from './useStreamingTextTask'
import { i18n } from '../i18n'

const { updateNodeData } = vi.hoisted(() => ({ updateNodeData: vi.fn() }))

vi.mock('@vue-flow/core', () => ({ useVueFlow: () => ({ updateNodeData }) }))

beforeEach(() => {
  setActivePinia(createPinia())
  updateNodeData.mockClear()
})

describe('streaming text task', () => {
  it('accumulates content, records the task and applies parsed success data', async () => {
    const authStore = useAuthStore()
    authStore.user = { credit_balance: 100 }
    authStore.refreshCredits = vi.fn().mockResolvedValue()
    const { runTextTask } = useStreamingTextTask('node-1')
    const streamer = vi.fn(async (_payload, onDelta, onMeta) => {
      onMeta('task-1', { template_version: 3, generated_locale: 'id' })
      onDelta('你好')
      onDelta('世界')
    })

    const content = await runTextTask(streamer, { prompt: 'test' }, {
      onSuccess: (value) => ({ result: value }),
    })

    expect(content).toBe('你好世界')
    expect(updateNodeData).toHaveBeenCalledWith('node-1', expect.objectContaining({ generationTaskId: 'task-1', templateVersion: 3 }))
    expect(updateNodeData).toHaveBeenLastCalledWith('node-1', expect.objectContaining({ result: '你好世界', status: 'ready', generated_locale: 'id' }))
    expect(authStore.refreshCredits).toHaveBeenCalledOnce()
  })

  it('preserves partial text and refreshes credits once after failure', async () => {
    const authStore = useAuthStore()
    authStore.user = { credit_balance: 100 }
    authStore.refreshCredits = vi.fn().mockResolvedValue()
    const { failure, runTextTask } = useStreamingTextTask('node-2')
    const streamer = async (_payload, onDelta) => {
      onDelta('部分结果')
      throw { response: { data: { message: '上游中断', error_key: 'upstream_unavailable' } } }
    }

    const result = await runTextTask(streamer, {}, {
      failureMessage: '生成失败',
      preservePartial: true,
    })

    expect(result).toBe(null)
    expect(failure.value).toBe(i18n.global.t('errors.upstream_unavailable'))
    expect(updateNodeData).toHaveBeenLastCalledWith('node-2', expect.objectContaining({
      status: 'failed',
      content: '部分结果',
      generationError: i18n.global.t('errors.upstream_unavailable'),
    }))
    expect(authStore.refreshCredits).toHaveBeenCalledOnce()
  })
})
