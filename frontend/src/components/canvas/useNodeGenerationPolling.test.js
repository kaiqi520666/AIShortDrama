import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick, reactive } from 'vue'
import { useNodeGenerationPolling } from './useNodeGenerationPolling'

const polling = vi.hoisted(() => ({
  startGenerationPolling: vi.fn(),
  stopGenerationPolling: vi.fn(),
}))

vi.mock('../../services/generationPolling', () => polling)

beforeEach(() => vi.clearAllMocks())

function createSubject() {
  const data = reactive({ generationTaskId: 'task-1', status: 'generating', generationPollingPaused: false })
  const updateNodeData = vi.fn((_, updates) => Object.assign(data, updates))
  const subject = useNodeGenerationPolling({
    getId: () => 'node-1',
    getData: () => data,
    getWorkspaceId: () => 'workspace-1',
    updateNodeData,
  })
  return { data, subject, updateNodeData }
}

describe('useNodeGenerationPolling', () => {
  it('starts immediately and resumes a paused task', () => {
    const { subject, updateNodeData } = createSubject()
    expect(polling.startGenerationPolling).toHaveBeenCalledWith('task-1', 'node-1', expect.any(Function), 'workspace-1')

    subject.resume()

    expect(updateNodeData).toHaveBeenCalledWith('node-1', { generationPollingPaused: false, generationError: '' })
    expect(polling.startGenerationPolling).toHaveBeenCalledTimes(2)
  })

  it('stops the old task when the node task changes', async () => {
    const { data } = createSubject()
    data.generationTaskId = 'task-2'
    await nextTick()

    expect(polling.stopGenerationPolling).toHaveBeenCalledWith('task-1')
    expect(polling.startGenerationPolling).toHaveBeenCalledWith('task-2', 'node-1', expect.any(Function), 'workspace-1')
  })
})
