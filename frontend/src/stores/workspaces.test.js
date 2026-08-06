import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { getWorkspace } from '../api/workspaces'
import { useWorkspaceStore } from './workspaces'

vi.mock('../api/workspaces', () => ({
  createWorkspace: vi.fn(),
  deleteWorkspace: vi.fn(),
  duplicateWorkspace: vi.fn(),
  getWorkspace: vi.fn(),
  listWorkspaces: vi.fn(),
  renameWorkspace: vi.fn(),
}))

function deferred() {
  let resolve
  const promise = new Promise((resolvePromise) => { resolve = resolvePromise })
  return { promise, resolve }
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
})

describe('workspace loading', () => {
  it('does not let an older response replace the latest workspace', async () => {
    const first = deferred()
    const second = deferred()
    getWorkspace
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)
    const store = useWorkspaceStore()

    const firstLoad = store.open('workspace-1')
    const secondLoad = store.open('workspace-2')
    second.resolve({ code: 0, data: { id: 'workspace-2' } })
    await secondLoad
    first.resolve({ code: 0, data: { id: 'workspace-1' } })
    await firstLoad

    expect(store.current).toEqual({ id: 'workspace-2' })
  })

  it('invalidates a pending request when the store closes', async () => {
    const pending = deferred()
    getWorkspace.mockImplementationOnce(() => pending.promise)
    const store = useWorkspaceStore()

    const request = store.open('workspace-1')
    store.close()
    pending.resolve({ code: 0, data: { id: 'workspace-1' } })
    await request

    expect(store.current).toBeNull()
  })

  it('forwards cancellation configuration to the API client', async () => {
    getWorkspace.mockResolvedValueOnce({ code: 0, data: { id: 'workspace-1' } })
    const signal = new AbortController().signal
    const store = useWorkspaceStore()

    await store.open('workspace-1', { signal })

    expect(getWorkspace).toHaveBeenCalledWith('workspace-1', { signal })
  })
})
