import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { saveWorkspaceCanvas } from '../api/workspaces'
import { seedModelCapabilities } from '../test/modelCapabilities'
import { seedContentTemplates } from '../test/contentTemplates'
import { useCanvasStore } from './canvas'

vi.mock('../api/workspaces', () => ({
  saveWorkspaceCanvas: vi.fn(async (_id, payload) => ({ code: 0, data: { version: payload.version + 1 } })),
}))

const readyNode = { id: 'text-1', type: 'text', position: { x: 0, y: 0 }, data: { status: 'ready' } }
const uploadingNode = { id: 'image-2', type: 'image', position: { x: 20, y: 20 }, data: { status: 'uploading' } }

beforeEach(() => {
  setActivePinia(createPinia())
  seedModelCapabilities()
  seedContentTemplates()
  vi.clearAllMocks()
})

describe('canvas transient uploads', () => {
  it('excludes uploading nodes and their relations from the saved payload', () => {
    const store = useCanvasStore()
    store.$patch({
      nodes: [readyNode, uploadingNode],
      edges: [{ id: 'edge-1', source: readyNode.id, target: uploadingNode.id }],
      groups: [{ id: 'group-1', title: '测试编组', nodeIds: [readyNode.id, uploadingNode.id] }],
    })

    const payload = store.canvasPayload()

    expect(payload.nodes.map((node) => node.id)).toEqual([readyNode.id])
    expect(payload.edges).toEqual([])
    expect(payload.groups).toEqual([])
  })

  it('removes stale uploading nodes when loading a workspace', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'general',
      canvas: { nodes: [readyNode, uploadingNode], edges: [], groups: [], sequence: 3 },
    })

    expect(store.nodes.map((node) => node.id)).toEqual([readyNode.id])
    expect(saveWorkspaceCanvas).toHaveBeenCalledOnce()
    expect(saveWorkspaceCanvas.mock.calls[0][1].version).toBe(1)
    expect(store.workspaceVersion).toBe(2)
  })
})

describe('canvas version conflicts', () => {
  it('persists an ecommerce v4 migration immediately', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 4,
      workspace_type: 'ecommerce',
      canvas: { schema_version: 3, nodes: [], edges: [], groups: [], sequence: 1 },
    })

    expect(saveWorkspaceCanvas).toHaveBeenCalledOnce()
    expect(saveWorkspaceCanvas).toHaveBeenCalledWith('workspace-1', expect.objectContaining({ schema_version: 4, version: 4 }))
    expect(store.workspaceVersion).toBe(5)
  })

  it('keeps a local ecommerce migration and exposes an automatic-save failure', async () => {
    saveWorkspaceCanvas.mockRejectedValueOnce(new Error('offline'))
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 4,
      workspace_type: 'ecommerce',
      canvas: { schema_version: 3, nodes: [], edges: [], groups: [], sequence: 1 },
    })

    expect(store.ready).toBe(true)
    expect(store.saveStatus).toBe('failed')
    expect(store.canvasPayload().schema_version).toBe(4)
  })

  it('forwards and updates the workspace version after a save', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 7,
      workspace_type: 'general',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    await store.saveCanvas()

    expect(saveWorkspaceCanvas).toHaveBeenCalledWith('workspace-1', expect.objectContaining({ version: 7 }))
    expect(store.workspaceVersion).toBe(8)
  })

  it('does not apply an old workspace save response after switching workspaces', async () => {
    let resolveSave
    saveWorkspaceCanvas.mockImplementationOnce(() => new Promise((resolve) => { resolveSave = resolve }))
    const store = useCanvasStore()
    await store.loadWorkspace({ id: 'workspace-1', version: 1, workspace_type: 'general', canvas: {} })
    const pending = store.saveCanvas()

    await store.loadWorkspace({ id: 'workspace-2', version: 9, workspace_type: 'general', canvas: {} })
    resolveSave({ code: 0, data: { version: 2 } })
    await pending

    expect(store.workspaceId).toBe('workspace-2')
    expect(store.workspaceVersion).toBe(9)
    expect(store.saveStatus).toBe('saved')
  })

  it('blocks later saves after the server reports a stale version', async () => {
    const conflict = Object.assign(new Error('conflict'), { response: { status: 409 } })
    saveWorkspaceCanvas.mockRejectedValueOnce(conflict)
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 3,
      workspace_type: 'general',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    await expect(store.saveCanvas()).rejects.toBe(conflict)
    await store.saveCanvas()

    expect(store.saveConflict).toBe(true)
    expect(store.saveStatus).toBe('conflict')
    expect(saveWorkspaceCanvas).toHaveBeenCalledOnce()
  })
})
