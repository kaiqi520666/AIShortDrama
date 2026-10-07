import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import { resolveAdminTaskReview } from './admin'

afterEach(() => vi.restoreAllMocks())

describe('admin review request', () => {
  it('uses the existing response envelope and passes cancellation to HTTP', async () => {
    const result = { code: 0, message: 'ok', data: { id: 'task-1', status: 'queued' } }
    const request = vi.spyOn(apiClient, 'post').mockResolvedValue({ data: result })
    const payload = { action: 'resume', reason: 'verified' }
    const controller = new AbortController()
    await expect(resolveAdminTaskReview('task-1', payload, { signal: controller.signal })).resolves.toEqual(result)
    expect(request).toHaveBeenCalledWith('/admin/tasks/task-1/resolve-review', payload, { signal: controller.signal })
  })
})
