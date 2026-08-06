import { describe, expect, it, vi } from 'vitest'
import { useWorkspaceCanvasSession } from './useWorkspaceCanvasSession'

function deferred() {
  let resolve
  let reject
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise
    reject = rejectPromise
  })
  return { promise, resolve, reject }
}

function setup(overrides = {}) {
  const loading = { showLoading: vi.fn(() => 'loading'), hideLoading: vi.fn() }
  const toast = { error: vi.fn() }
  const workspaceStore = {
    open: vi.fn(async (id) => ({ id })),
    fetch: vi.fn(async (id) => ({ id })),
  }
  const capabilityStore = { load: vi.fn(async () => ({})) }
  return {
    ...useWorkspaceCanvasSession({ workspaceStore, capabilityStore, loading, toast, ...overrides }),
    loading,
    toast,
    workspaceStore,
    capabilityStore,
  }
}

describe('workspace canvas session', () => {
  it('keeps the loading task until the canvas signals ready', async () => {
    const session = setup()

    await expect(session.load('workspace-1', { initial: true })).resolves.toEqual({ id: 'workspace-1' })
    expect(session.loading.hideLoading).not.toHaveBeenCalled()

    session.finishLoading()
    expect(session.loading.hideLoading).toHaveBeenCalledWith('loading')
  })

  it('cancels a stale workspace request and ignores its response', async () => {
    const first = deferred()
    const second = deferred()
    const workspaceStore = {
      open: vi.fn(),
      fetch: vi.fn()
        .mockImplementationOnce(() => first.promise)
        .mockImplementationOnce(() => second.promise),
    }
    const session = setup({ workspaceStore })

    const firstLoad = session.load('workspace-1', { commit: false })
    const secondLoad = session.load('workspace-2', { commit: false })
    second.resolve({ id: 'workspace-2' })
    await expect(secondLoad).resolves.toEqual({ id: 'workspace-2' })
    first.resolve({ id: 'workspace-1' })
    await expect(firstLoad).resolves.toBeNull()
  })

  it('aborts the previous request before starting a route update load', async () => {
    const requests = []
    const workspaceStore = {
      open: vi.fn(),
      fetch: vi.fn((_id, { signal }) => {
        const request = deferred()
        requests.push({ signal, ...request })
        return request.promise
      }),
    }
    const session = setup({ workspaceStore })

    const firstLoad = session.load('workspace-1', { commit: false })
    const secondLoad = session.load('workspace-2', { commit: false })

    expect(requests[0].signal.aborted).toBe(true)
    requests[1].resolve({ id: 'workspace-2' })
    await expect(secondLoad).resolves.toEqual({ id: 'workspace-2' })
    requests[0].resolve({ id: 'workspace-1' })
    await expect(firstLoad).resolves.toBeNull()
  })

  it('shows initial errors inline and route update errors as a toast', async () => {
    const error = new Error('offline')
    const initial = setup({ workspaceStore: { open: vi.fn(async () => { throw error }), fetch: vi.fn() } })
    await expect(initial.load('workspace-1', { initial: true })).resolves.toBeNull()
    expect(initial.loadError.value).toBe('offline')

    const update = setup({ workspaceStore: { open: vi.fn(), fetch: vi.fn(async () => { throw error }) } })
    await expect(update.load('workspace-2', { commit: false })).resolves.toBeNull()
    expect(update.toast.error).toHaveBeenCalledWith('offline')
  })
})
