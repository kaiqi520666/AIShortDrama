import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { seedModelCapabilities } from '../test/modelCapabilities'
import { seedContentTemplates } from '../test/contentTemplates'
import { useCanvasStore } from './canvas'

const readyNode = { id: 'text-1', type: 'text', position: { x: 0, y: 0 }, data: { status: 'ready' } }

beforeEach(() => {
  setActivePinia(createPinia())
  seedModelCapabilities()
  seedContentTemplates()
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

describe('canvas connections and node packs', () => {
  it('locks automatic workflow nodes and edges while keeping basic nodes editable', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1', version: 1, workspace_type: 'ecommerce', canvas: { schema_version: 4, nodes: [], edges: [], groups: [], sequence: 1 },
    })
    const productId = store.addEcommerceWorkflow('product', { x: 0, y: 0 })
    const workflowId = store.nodes.find((node) => node.id === productId).data.workflowId
    const storyboard = store.nodes.find((node) => node.data.workflowRole === 'storyboard')
    const managedEdge = store.edges[0]
    const basicId = store.addNode('image', { x: -900, y: 0 })

    expect(store.addEdge({ source: basicId, target: productId })).toBe(true)
    const extraStoryboardId = store.addNode('product_storyboard', { x: 900, y: 500 }, null, true)
    expect(store.addEdge({ source: productId, target: extraStoryboardId })).toBe(true)
    expect(store.edges.find((edge) => edge.source === basicId && edge.target === productId)).not.toHaveProperty('workflowId')
    expect(store.edges.find((edge) => edge.source === productId && edge.target === extraStoryboardId)).not.toHaveProperty('workflowId')
    expect(store.deleteEdge(managedEdge.id)).toBe(false)
    expect(store.deleteNode(storyboard.id)).toBe('workflow_locked')
    expect(store.deleteNode(productId)).toBe('workflow_root')
    expect(store.deleteNodes([storyboard.id])).toBe(false)
    expect(store.duplicateNodes([productId])).toEqual([])
    store.selectNodes([productId, storyboard.id])
    expect(store.groupSelected()).toBe(false)

    expect(store.deleteWorkflow(workflowId)).toBe(true)
    expect(store.nodes.map((node) => node.id)).toEqual([basicId, extraStoryboardId])
    expect(store.edges).toEqual([])
  })

  it('allows ordinary basic-node connections and deletion', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1', version: 1, workspace_type: 'ecommerce', canvas: { schema_version: 4, nodes: [], edges: [], groups: [], sequence: 1 },
    })
    const imageId = store.addNode('image', { x: 0, y: 0 })
    const videoId = store.addNode('video', { x: 400, y: 0 })

    expect(store.addEdge({ source: imageId, target: videoId })).toBe(true)
    expect(store.deleteEdge(store.edges[0].id)).toBe(true)
    expect(store.deleteNode(imageId)).toBe(true)
  })

  it('finds an incoming node by its target handle', () => {
    const store = useCanvasStore()
    store.$patch({
      nodes: [{ id: 'product-1', type: 'product', data: {} }, { id: 'visual-1', type: 'product_visual', data: {} }],
      edges: [{ id: 'edge-1', source: 'product-1', target: 'visual-1', targetHandle: 'product' }],
    })

    expect(store.incomingNodeByHandle('visual-1', 'product')).toEqual(expect.objectContaining({ id: 'product-1' }))
    expect(store.incomingNodeByHandle('visual-1', 'reference')).toBeUndefined()
  })

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

  it('loads the workspace type and rejects nodes outside its pack', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'general',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    expect(store.workspaceType).toBe('general')
    expect(store.addNode('product', { x: 0, y: 0 })).toBeUndefined()
    expect(store.addNode('image', { x: 0, y: 0 })).toBe('image-1')
  })
})
