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

  it('duplicates a node with every upstream node and internal edge', () => {
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

    const ids = store.duplicateUpstream('c')

    expect(ids).toEqual(['text-10', 'text-11', 'text-12'])
    expect(store.nodes.slice(-3).map((node) => node.position)).toEqual([{ x: 56, y: 56 }, { x: 156, y: 56 }, { x: 256, y: 56 }])
    expect(store.edges.slice(-2)).toEqual([
      expect.objectContaining({ source: 'text-10', target: 'text-11' }),
      expect.objectContaining({ source: 'text-11', target: 'text-12' }),
    ])
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
