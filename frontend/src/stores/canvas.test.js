import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { saveWorkspaceCanvas } from '../api/workspaces'
import { useCanvasStore } from './canvas'

vi.mock('../api/workspaces', () => ({
  saveWorkspaceCanvas: vi.fn(async () => ({ code: 0 })),
}))

const readyNode = { id: 'text-1', type: 'text', position: { x: 0, y: 0 }, data: { status: 'ready' } }
const uploadingNode = { id: 'image-2', type: 'image', position: { x: 20, y: 20 }, data: { status: 'uploading' } }

beforeEach(() => {
  setActivePinia(createPinia())
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
      canvas: { nodes: [readyNode, uploadingNode], edges: [], groups: [], sequence: 3 },
    })

    expect(store.nodes.map((node) => node.id)).toEqual([readyNode.id])
    expect(saveWorkspaceCanvas).toHaveBeenCalledOnce()
  })
})
