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
      workspace_type: 'general',
      canvas: { nodes: [readyNode, uploadingNode], edges: [], groups: [], sequence: 3 },
    })

    expect(store.nodes.map((node) => node.id)).toEqual([readyNode.id])
    expect(saveWorkspaceCanvas).toHaveBeenCalledOnce()
  })
})

describe('canvas grouping and duplication', () => {
  it('merges complete groups touched by selected nodes', () => {
    const store = useCanvasStore()
    store.$patch({
      nodes: ['a', 'b', 'c', 'd'].map((id) => ({ id, type: 'text', position: { x: 0, y: 0 }, selected: ['a', 'c'].includes(id), data: {} })),
      groups: [{ id: 'group-1', title: '第一组', nodeIds: ['a', 'b'] }, { id: 'group-2', title: '第二组', nodeIds: ['c', 'd'] }],
    })

    store.groupSelected()

    expect(store.groups).toEqual([{ id: 'group-1', title: '第一组', nodeIds: ['a', 'b', 'c', 'd'] }])
  })

  it('duplicates selected nodes with internal edges and group membership', () => {
    const store = useCanvasStore()
    store.$patch({
      sequence: 10,
      nodes: [
        { id: 'text-1', type: 'text', position: { x: 10, y: 20 }, selected: true, data: { title: '文本' } },
        { id: 'image-2', type: 'image', position: { x: 100, y: 20 }, selected: true, data: { title: '图片' } },
        { id: 'video-3', type: 'video', position: { x: 200, y: 20 }, selected: false, data: { title: '视频' } },
      ],
      edges: [{ id: 'edge-1', source: 'text-1', target: 'image-2', type: 'cinematic' }, { id: 'edge-2', source: 'image-2', target: 'video-3', type: 'cinematic' }],
      groups: [{ id: 'group-1', title: '组合', nodeIds: ['text-1', 'image-2'] }],
    })

    const ids = store.duplicateSelected()

    expect(ids).toEqual(['text-10', 'image-11'])
    expect(store.nodes.filter((node) => node.selected).map((node) => node.id)).toEqual(ids)
    expect(store.edges.filter((edge) => ids.includes(edge.source) || ids.includes(edge.target))).toEqual([
      expect.objectContaining({ source: 'text-10', target: 'image-11' }),
    ])
    expect(store.groups).toContainEqual(expect.objectContaining({ title: '组合 副本', nodeIds: ids }))
  })

  it('duplicates only the node and reconnects its existing inputs', () => {
    const store = useCanvasStore()
    store.$patch({
      sequence: 10,
      nodes: ['a', 'b', 'c', 'd'].map((id, index) => ({ id, type: 'text', position: { x: index * 100, y: 0 }, data: { title: id } })),
      edges: [
        { id: 'edge-1', source: 'a', target: 'b' },
        { id: 'edge-2', source: 'b', target: 'c' },
        { id: 'edge-3', source: 'a', target: 'd' },
      ],
    })

    const id = store.duplicateWithInputs('c')

    expect(id).toBe('text-10')
    expect(store.nodes.at(-1)).toEqual(expect.objectContaining({ id, position: { x: 256, y: 56 } }))
    expect(store.edges.at(-1)).toEqual(expect.objectContaining({ source: 'b', target: id }))
  })

  it('moves selected nodes out of a group and removes groups with fewer than two nodes', () => {
    const store = useCanvasStore()
    store.$patch({ groups: [{ id: 'group-1', title: '组合', nodeIds: ['a', 'b', 'c'] }] })

    store.removeNodesFromGroup('group-1', ['a'])
    expect(store.groups[0].nodeIds).toEqual(['b', 'c'])

    store.removeNodesFromGroup('group-1', ['b'])
    expect(store.groups).toEqual([])
  })

  it('deletes multiple nodes with their edges and group membership', () => {
    const store = useCanvasStore()
    store.$patch({
      nodes: ['a', 'b', 'c'].map((id) => ({ id, type: 'text', data: {} })),
      edges: [{ id: 'edge-1', source: 'a', target: 'b' }, { id: 'edge-2', source: 'b', target: 'c' }],
      groups: [{ id: 'group-1', title: '组合', nodeIds: ['a', 'b', 'c'] }],
    })

    store.deleteNodes(['a', 'b'])

    expect(store.nodes.map((node) => node.id)).toEqual(['c'])
    expect(store.edges).toEqual([])
    expect(store.groups).toEqual([])
  })

  it('deletes a group with its nodes and connected edges', () => {
    const store = useCanvasStore()
    store.$patch({
      nodes: ['a', 'b', 'c'].map((id) => ({ id, type: 'text', position: { x: 0, y: 0 }, data: {} })),
      edges: [{ id: 'edge-1', source: 'a', target: 'b' }, { id: 'edge-2', source: 'b', target: 'c' }],
      groups: [{ id: 'group-1', title: '待删除', nodeIds: ['a', 'b'] }],
    })

    store.deleteGroup('group-1')

    expect(store.nodes.map((node) => node.id)).toEqual(['c'])
    expect(store.edges).toEqual([])
    expect(store.groups).toEqual([])
  })

  it('renames a node', () => {
    const store = useCanvasStore()
    store.$patch({ nodes: [{ ...readyNode, data: { ...readyNode.data, title: '旧名称' } }] })

    store.renameNode(readyNode.id, ' 新名称 ')

    expect(store.nodes[0].data.title).toBe('新名称')
  })
})

describe('audio reference connections', () => {
  it('enforces mutually exclusive and counted media references in the store', () => {
    const store = useCanvasStore()
    store.$patch({
      nodes: [
        { id: 'image-1', type: 'image', data: {} },
        { id: 'audio-1', type: 'audio', data: {} },
        { id: 'audio-2', type: 'audio', data: {} },
      ],
      edges: [{ id: 'edge-1', source: 'image-1', target: 'audio-2' }],
    })

    expect(store.addEdge({ source: 'audio-1', target: 'audio-2' })).toBe(false)
    expect(store.edges).toHaveLength(1)
  })
})

describe('canvas node packs', () => {
  it('loads the workspace type and rejects nodes outside its pack', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      workspace_type: 'drama',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    expect(store.workspaceType).toBe('drama')
    expect(store.addNode('product', { x: 0, y: 0 })).toBeUndefined()
    expect(store.addNode('image', { x: 0, y: 0 })).toBe('image-1')
  })

  it('creates ecommerce business nodes with persistent defaults', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    const productId = store.addNode('product', { x: 0, y: 0 })
    const copyId = store.addNode('selling_copy', { x: 500, y: 0 }, productId)

    expect(productId).toBe('product-2')
    expect(store.nodes[0]).toEqual(expect.objectContaining({ id: 'image-1', data: expect.objectContaining({ title: '商品参考图', assetSource: 'upload' }) }))
    expect(store.nodes[1].data).toEqual(expect.objectContaining({ product: expect.objectContaining({ name: '', sellingPoints: '' }), prompt: expect.stringContaining('JSON') }))
    expect(copyId).toBe('selling_copy-3')
    expect(store.edges).toEqual([
      expect.objectContaining({ source: 'image-1', target: productId }),
      expect.objectContaining({ source: productId, target: copyId }),
    ])
  })

  it('uses an existing image when product creation is contextual', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    const imageId = store.addNode('image', { x: 0, y: 0 })
    const productId = store.addNode('product', { x: 460, y: 0 }, imageId)

    expect(store.nodes).toHaveLength(2)
    expect(store.edges[0]).toEqual(expect.objectContaining({ source: imageId, target: productId }))
  })
})
