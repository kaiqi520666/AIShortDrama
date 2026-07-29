import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { saveWorkspaceCanvas } from '../api/workspaces'
import { useCanvasStore } from './canvas'

vi.mock('../api/workspaces', () => ({
  saveWorkspaceCanvas: vi.fn(async (_id, payload) => ({ code: 0, data: { version: payload.version + 1 } })),
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
      version: 1,
      workspace_type: 'drama',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    expect(store.workspaceType).toBe('drama')
    expect(store.addNode('product', { x: 0, y: 0 })).toBeUndefined()
    expect(store.addNode('image', { x: 0, y: 0 })).toBe('image-1')
  })

  it('creates a character workflow from world context with an optional reference input', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'drama',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    const worldId = store.addNode('world', { x: 0, y: 0 })
    const characterId = store.addNode('character', { x: 500, y: 0 }, worldId)

    expect(characterId).toBe('character-3')
    expect(store.nodes).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: worldId, type: 'world' }),
      expect.objectContaining({ id: 'image-2', data: expect.objectContaining({ title: '角色参考图', resourceType: 'character' }) }),
      expect.objectContaining({ id: characterId, data: expect.objectContaining({ workflowStep: 'profile', aspectRatio: '3:4', mainReferenceNodeId: '' }) }),
    ]))
    expect(store.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: worldId, target: characterId, targetHandle: 'world' }),
      expect.objectContaining({ source: 'image-2', target: characterId, targetHandle: 'reference' }),
    ]))
  })

  it('creates three character image nodes with shared character and optional image references', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'drama',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })
    const worldId = store.addNode('world', { x: 0, y: 0 })
    const characterId = store.addNode('character', { x: 500, y: 0 }, worldId)
    const ids = store.addCharacterVisualNodes(characterId, 'image-2', [
      { id: 'full-body', label: '正面全身', prompt: '全身设定' },
      { id: 'portrait', label: '半身肖像', prompt: '半身设定' },
      { id: 'turnaround', label: '角色三视图', prompt: '三视图设定' },
    ], { model: 'gpt-image-2', aspectRatio: '3:4', resolution: '2K' })

    expect(ids).toEqual(['image-4', 'image-5', 'image-6'])
    expect(store.nodes.find((node) => node.id === ids[0]).data).toEqual(expect.objectContaining({
      title: '正面全身', characterSourceId: characterId, prompt: '全身设定', model: 'gpt-image-2', aspectRatio: '3:4', resolution: '2K',
    }))
    expect(store.edges.filter((edge) => ids.includes(edge.target))).toHaveLength(6)
  })

  it('creates an ecommerce product node with persistent defaults', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    const productId = store.addNode('product', { x: 0, y: 0 })
    expect(productId).toBe('product-2')
    expect(store.nodes[0]).toEqual(expect.objectContaining({
      id: 'image-1',
      position: { x: -460, y: 3 },
      data: expect.objectContaining({ title: '商品参考图', assetSource: 'upload' }),
    }))
    expect(store.nodes[1].data).toEqual(expect.objectContaining({
      workflowStep: 'recognition',
      product: expect.objectContaining({ name: '', sellingPoints: '', additionalInfo: '' }),
      textModel: 'qwen3.7-plus',
      imageModel: 'gpt-image-2',
      items: expect.arrayContaining([expect.objectContaining({ id: 'white-bg', enabled: true })]),
      prompt: '',
    }))
    expect(store.edges).toEqual([
      expect.objectContaining({ source: 'image-1', target: productId }),
    ])
  })

  it('uses an existing image when product creation is contextual', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    const imageId = store.addNode('image', { x: 0, y: 0 })
    const productId = store.addNode('product', { x: 460, y: 0 }, imageId)

    expect(store.nodes).toHaveLength(2)
    expect(store.edges[0]).toEqual(expect.objectContaining({ source: imageId, target: productId }))
  })

  it('creates an outfit workflow with garment and model inputs', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    const outfitId = store.addNode('outfit', { x: 500, y: 300 })

    expect(outfitId).toBe('outfit-3')
    expect(store.nodes).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'image-1', data: expect.objectContaining({ title: '服饰参考图', assetSource: 'upload', resourceType: 'garment' }) }),
      expect.objectContaining({ id: 'image-2', data: expect.objectContaining({ title: '模特参考图', assetSource: 'upload', resourceType: 'model' }) }),
      expect.objectContaining({ id: outfitId, type: 'outfit', data: expect.objectContaining({ title: '服饰穿搭 3', textModel: 'qwen3.7-plus', imageModel: 'gpt-image-2', aspectRatio: '1:1', resolution: '1K', sceneIds: ['studio'], customScene: '', generatedNodeIds: [] }) }),
    ]))
    expect(store.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: 'image-1', target: outfitId, targetHandle: 'garment' }),
      expect.objectContaining({ source: 'image-2', target: outfitId, targetHandle: 'model' }),
    ]))
    expect(store.nodes.filter((node) => node.selected).map((node) => node.id)).toEqual([outfitId])
  })

  it('creates planned outfit image nodes with shared references and settings', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })
    const outfitId = store.addNode('outfit', { x: 500, y: 300 })
    const resultIds = store.addOutfitVisualNodes(outfitId, 'image-1', 'image-2', [
      { id: 'studio', label: '纯色棚拍', prompt: '棚拍穿搭效果' },
      { id: 'street', label: '都市街头', prompt: '街头穿搭效果' },
    ], {
      model: 'gpt-image-2', aspectRatio: '3:4', resolution: '2K',
    })

    expect(resultIds).toEqual(['image-4', 'image-5'])
    expect(store.nodes.find((node) => node.id === resultIds[0]).data).toEqual(expect.objectContaining({
      title: '纯色棚拍', outfitSourceId: outfitId, status: 'empty', prompt: '棚拍穿搭效果', model: 'gpt-image-2', aspectRatio: '3:4', resolution: '2K',
    }))
    expect(store.edges.filter((edge) => edge.target === resultIds[0])).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: outfitId }),
      expect.objectContaining({ source: 'image-1' }),
      expect.objectContaining({ source: 'image-2' }),
    ]))
    expect(store.edges.filter((edge) => resultIds.includes(edge.target))).toHaveLength(6)
    expect(store.nodes.filter((node) => node.selected).map((node) => node.id)).toEqual([resultIds[0]])
  })

  it('creates planned image nodes from product creation with shared settings and references', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })
    const productId = store.addNode('product', { x: 0, y: 0 })
    const referenceId = store.nodes[0].id
    store.nodes[0].data.asset = 'https://example.com/product.png'

    const ids = store.addProductVisualNodes(productId, productId, referenceId, [
      { id: 'white-bg', label: '白底图', prompt: '纯白背景商品图' },
      { id: 'first-screen', label: '首屏主视觉', prompt: '首屏主视觉商品图' },
    ], { model: 'gpt-image-2', aspectRatio: '1:1', resolution: '1K' })

    expect(ids).toEqual(['image-3', 'image-4'])
    expect(store.nodes.find((node) => node.id === ids[0]).data).toEqual(expect.objectContaining({
      title: '白底图', prompt: '纯白背景商品图', model: 'gpt-image-2', aspectRatio: '1:1', resolution: '1K',
    }))
    expect(store.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: referenceId, target: ids[0] }),
      expect.objectContaining({ source: productId, target: ids[0] }),
      expect.objectContaining({ source: referenceId, target: ids[1] }),
      expect.objectContaining({ source: productId, target: ids[1] }),
    ]))
    expect(store.edges.filter((edge) => ids.includes(edge.target))).toHaveLength(4)
  })
})
