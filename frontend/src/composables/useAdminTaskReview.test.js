import { beforeEach, describe, expect, it, vi } from 'vitest'
import { resolveAdminTaskReview } from '../api/admin'
import { useAdminTaskReview } from './useAdminTaskReview'

const { confirmMutation } = vi.hoisted(() => ({ confirmMutation: vi.fn() }))
vi.mock('./useAdminMutation', () => ({ useAdminMutation: () => ({ confirmMutation }) }))
vi.mock('../api/admin', () => ({ resolveAdminTaskReview: vi.fn() }))

beforeEach(() => {
  vi.clearAllMocks()
  confirmMutation.mockResolvedValue(true)
  resolveAdminTaskReview.mockResolvedValue({ code: 0, data: { id: 'task-1', status: 'queued' } })
})

function createReview(overrides = {}, onResolved = vi.fn()) {
  const controls = useAdminTaskReview({ onResolved })
  controls.openReview({ id: 'task-1', status: 'needs_review', task_type: 'image', ...overrides })
  controls.review.reason = '  已核查上游任务  '
  return { ...controls, onResolved }
}

describe('admin task review', () => {
  it('continues a verified remote task and refreshes from the returned task', async () => {
    const controls = createReview()
    controls.review.providerTaskId = ' remote-1 '
    expect(await controls.submitReview()).toBe(true)
    expect(resolveAdminTaskReview).toHaveBeenCalledWith('task-1', {
      action: 'resume', reason: '已核查上游任务', provider_task_id: 'remote-1',
    })
    expect(controls.onResolved).toHaveBeenCalledWith({ id: 'task-1', status: 'queued' })
    expect(controls.review.task).toBeNull()
    expect(controls.review.submitting).toBe(false)
  })

  it.each(['fail', 'cancel'])('does not attach a provider task ID to %s', async (action) => {
    const controls = createReview({ provider_task_id: 'remote-1' })
    controls.review.action = action
    await controls.submitReview()
    expect(resolveAdminTaskReview).toHaveBeenCalledWith('task-1', {
      action, reason: '已核查上游任务',
    })
  })

  it('keeps local review inputs when confirmation is declined', async () => {
    confirmMutation.mockResolvedValue(false)
    const controls = createReview()
    expect(await controls.submitReview()).toBe(false)
    expect(resolveAdminTaskReview).not.toHaveBeenCalled()
    expect(controls.review.task.id).toBe('task-1')
    expect(controls.review.reason).toBe('  已核查上游任务  ')
    expect(controls.review.submitting).toBe(false)
  })

  it('prevents duplicate submission and closing during confirmation', async () => {
    let confirm
    confirmMutation.mockImplementation(() => new Promise((resolve) => { confirm = resolve }))
    const controls = createReview()
    const pending = controls.submitReview()
    controls.closeReview()
    expect(controls.review.task.id).toBe('task-1')
    expect(await controls.submitReview()).toBe(false)
    expect(confirmMutation).toHaveBeenCalledTimes(1)
    confirm(true)
    await pending
    expect(resolveAdminTaskReview).toHaveBeenCalledTimes(1)
  })

  it('preserves the reason for retry when the request fails', async () => {
    resolveAdminTaskReview.mockRejectedValue(new Error('network failure'))
    const controls = createReview()
    await expect(controls.submitReview()).rejects.toThrow('network failure')
    expect(controls.onResolved).not.toHaveBeenCalled()
    expect(controls.review.task.id).toBe('task-1')
    expect(controls.review.reason).toBe('  已核查上游任务  ')
    expect(controls.review.submitting).toBe(false)
  })

  it('requires a reason and only opens tasks waiting for review', async () => {
    const controls = createReview()
    controls.review.reason = '  '
    expect(await controls.submitReview()).toBe(false)
    expect(confirmMutation).not.toHaveBeenCalled()
    controls.closeReview()
    controls.openReview({ id: 'done', status: 'succeeded', task_type: 'image' })
    expect(controls.review.task).toBeNull()
  })

  it('defaults text tasks to cancel and does not send IDs for synchronous audio', async () => {
    const text = createReview({ task_type: 'text' })
    expect(text.review.action).toBe('cancel')
    const audio = createReview({ task_type: 'audio', provider_task_id: 'legacy-id' })
    await audio.submitReview()
    expect(resolveAdminTaskReview).toHaveBeenCalledWith('task-1', {
      action: 'resume', reason: '已核查上游任务',
    })
  })
})
