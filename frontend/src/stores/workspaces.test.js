import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createWorkspace, getWorkspace } from '../api/workspaces'
import { i18n } from '../i18n'
import { useWorkspaceStore } from './workspaces'

let previousLocale

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
  previousLocale = i18n.global.locale.value
})

afterEach(() => {
  i18n.global.locale.value = previousLocale
  vi.restoreAllMocks()
})

describe('workspace creation', () => {
  it('uses sequential numeric names for new workspace cards', async () => {
    createWorkspace
      .mockResolvedValueOnce({ code: 0, data: { id: 'workspace-1', name: '01' } })
      .mockResolvedValueOnce({ code: 0, data: { id: 'workspace-2', name: '02' } })
    const store = useWorkspaceStore()

    await store.create('general')
    await store.create('general')

    expect(createWorkspace).toHaveBeenNthCalledWith(1, '01', 'general')
    expect(createWorkspace).toHaveBeenNthCalledWith(2, '02', 'general')
  })

  it('keeps numeric names when switching language and workspace type', async () => {
    createWorkspace
      .mockResolvedValueOnce({ code: 0, data: { id: 'workspace-1', name: '01' } })
      .mockResolvedValueOnce({ code: 0, data: { id: 'workspace-2', name: '02' } })
    const store = useWorkspaceStore()

    i18n.global.locale.value = 'zh-CN'
    await store.create('general')
    i18n.global.locale.value = 'id'
    await store.create('ecommerce')

    expect(createWorkspace).toHaveBeenNthCalledWith(1, '01', 'general')
    expect(createWorkspace).toHaveBeenNthCalledWith(2, '02', 'ecommerce')
    expect(store.items.map(({ name }) => name)).toEqual(['02', '01'])
  })

  it('counts existing projects without changing their names', async () => {
    const existing = [
      { id: 'workspace-1', name: '\u672a\u547d\u540d\u901a\u7528\u9879\u76ee' },
      { id: 'workspace-2', name: 'Custom project' },
    ]
    const store = useWorkspaceStore()
    store.items = [...existing]
    createWorkspace.mockResolvedValueOnce({ code: 0, data: { id: 'workspace-3', name: '03' } })

    await store.create('general')

    expect(createWorkspace).toHaveBeenCalledWith('03', 'general')
    expect(store.items.slice(1)).toEqual(existing)
  })

  it('does not add an item or consume a number when creation fails', async () => {
    const existing = { id: 'workspace-1', name: 'Custom project' }
    const store = useWorkspaceStore()
    store.items = [existing]
    createWorkspace
      .mockResolvedValueOnce({ code: 1, message: 'Creation failed' })
      .mockResolvedValueOnce({ code: 0, data: { id: 'workspace-2', name: '02' } })

    await expect(store.create('general')).rejects.toThrow('Creation failed')
    expect(store.items).toEqual([existing])
    await store.create('general')

    expect(createWorkspace).toHaveBeenNthCalledWith(1, '02', 'general')
    expect(createWorkspace).toHaveBeenNthCalledWith(2, '02', 'general')
    expect(store.items).toHaveLength(2)
  })

  it('rejects an unsupported workspace type before calling the API', async () => {
    const store = useWorkspaceStore()

    await expect(store.create('unsupported')).rejects.toThrow('unsupported')

    expect(createWorkspace).not.toHaveBeenCalled()
    expect(store.items).toEqual([])
  })

  it('does not truncate a three-digit project number', async () => {
    const store = useWorkspaceStore()
    store.items = Array.from({ length: 99 }, (_, index) => ({ id: `workspace-${index + 1}` }))
    createWorkspace.mockResolvedValueOnce({ code: 0, data: { id: 'workspace-100', name: '100' } })

    await store.create('ecommerce')

    expect(createWorkspace).toHaveBeenCalledWith('100', 'ecommerce')
    expect(store.items[0].name).toBe('100')
  })
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
