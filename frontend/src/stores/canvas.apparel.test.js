import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { seedModelCapabilities } from '../test/modelCapabilities'
import { seedContentTemplates } from '../test/contentTemplates'
import { useCanvasStore } from './canvas'

beforeEach(() => {
  setActivePinia(createPinia())
  seedModelCapabilities()
  seedContentTemplates()
})

describe('canvas apparel workflows', () => {
  it('creates an apparel profile with an image input', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    const apparelId = store.addNode('apparel', { x: 460, y: 0 })

    expect(apparelId).toBe('apparel-2')
    expect(store.nodes).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'image-1', data: expect.objectContaining({ title: '服饰参考图', resourceType: 'garment' }) }),
      expect.objectContaining({ id: apparelId, data: expect.objectContaining({ compositionType: 'single', summary: '', items: [], prompt: '' }) }),
    ]))
    expect(store.edges).toEqual([expect.objectContaining({ source: 'image-1', target: apparelId })])
  })

  it('creates an outfit workflow with apparel profile and model inputs', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    const outfitId = store.addNode('outfit', { x: 500, y: 300 })

    expect(outfitId).toBe('outfit-4')
    expect(store.nodes).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'image-1', data: expect.objectContaining({ title: '服饰参考图', assetSource: 'upload', resourceType: 'garment' }) }),
      expect.objectContaining({ id: 'apparel-2', type: 'apparel', data: expect.objectContaining({ title: '服饰资料 2', items: [] }) }),
      expect.objectContaining({ id: 'image-3', data: expect.objectContaining({ title: '模特参考图', assetSource: 'upload', resourceType: 'model' }) }),
      expect.objectContaining({ id: outfitId, type: 'outfit', data: expect.objectContaining({ title: '服饰穿搭 4', textModel: 'gpt-5.6-sol', imageModel: 'gpt-image-2', aspectRatio: '9:16', resolution: '1K', moduleIds: ['front', 'three-quarter', 'back', 'turn', 'fabric', 'lifestyle'], customRequirement: '', generatedNodeIds: [] }) }),
    ]))
    expect(store.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: 'image-1', target: 'apparel-2' }),
      expect.objectContaining({ source: 'apparel-2', target: outfitId, targetHandle: 'apparel' }),
      expect.objectContaining({ source: 'image-3', target: outfitId, targetHandle: 'model' }),
    ]))
    expect(store.nodes.filter((node) => node.selected).map((node) => node.id)).toEqual([outfitId])
  })

  it('creates apparel storyboard inputs for apparel, role, and scene', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    const storyboardId = store.addNode('apparel_storyboard', { x: 900, y: 300 })

    expect(storyboardId).toBe('apparel_storyboard-5')
    expect(store.nodes).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'apparel-2' }),
      expect.objectContaining({ id: 'image-3', data: expect.objectContaining({ title: '角色节点', resourceType: 'model', inputRole: 'role' }) }),
      expect.objectContaining({ id: 'image-4', data: expect.objectContaining({ title: '场景节点', inputRole: 'scene' }) }),
      expect.objectContaining({ id: storyboardId }),
    ]))
    expect(store.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: 'apparel-2', target: storyboardId, targetHandle: 'apparel' }),
      expect.objectContaining({ source: 'image-3', target: storyboardId, targetHandle: 'model' }),
      expect.objectContaining({ source: 'image-4', target: storyboardId, targetHandle: 'scene' }),
    ]))
    expect(store.nodes.filter((node) => node.selected).map((node) => node.id)).toEqual([storyboardId])
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
    const resultIds = store.addOutfitVisualNodes(outfitId, 'image-1', 'image-3', [
      { id: 'front', label: '正面全身', category: 'view', categoryLabel: '基础视角', prompt: '正面穿搭效果' },
      { id: 'street', label: '街头穿搭', category: 'lifestyle', categoryLabel: '内容场景', prompt: '街头穿搭效果' },
    ], {
      model: 'gpt-image-2', aspectRatio: '3:4', resolution: '2K',
    })

    expect(resultIds).toEqual(['image-5', 'image-6'])
    expect(store.nodes.find((node) => node.id === resultIds[0]).data).toEqual(expect.objectContaining({
      title: '正面全身', outfitSourceId: outfitId, outfitMaterialId: 'front', outfitMaterialCategory: 'view', outfitMaterialCategoryLabel: '基础视角', resourceType: 'outfit-material', status: 'empty', prompt: '正面穿搭效果', model: 'gpt-image-2', aspectRatio: '3:4', resolution: '2K',
    }))
    expect(store.edges.filter((edge) => edge.target === resultIds[0])).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: outfitId }),
      expect.objectContaining({ source: 'image-1' }),
      expect.objectContaining({ source: 'image-3' }),
    ]))
    expect(store.edges.filter((edge) => resultIds.includes(edge.target))).toHaveLength(6)
    expect(store.nodes.filter((node) => node.selected).map((node) => node.id)).toEqual([resultIds[0]])
  })

  it('creates one apparel storyboard image and one standard video node', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })
    const apparelId = store.addNode('apparel', { x: 500, y: 300 })
    const garmentId = store.edges.find((edge) => edge.target === apparelId)?.source
    const modelId = store.addNode('image', { x: 700, y: 260 })
    const sceneId = store.addNode('image', { x: 700, y: 420 })
    store.nodes.find((node) => node.id === modelId).data = { title: '模特参考图', resourceType: 'model', asset: 'https://example.com/model.png' }
    store.nodes.find((node) => node.id === sceneId).data = { title: '场景参考图', resourceType: 'asset', asset: 'https://example.com/scene.png' }
    const storyboardId = store.addNode('apparel_storyboard', { x: 1000, y: 300 })
    store.addEdge({ source: apparelId, target: storyboardId, targetHandle: 'apparel' })
    store.addEdge({ source: modelId, target: storyboardId, targetHandle: 'model' })
    store.addEdge({ source: sceneId, target: storyboardId, targetHandle: 'scene' })

    const resultIds = store.addApparelStoryboardNodes(storyboardId, garmentId, modelId, sceneId, {
      templateId: 'apparel-showcase', title: '服饰展示', duration: 10, shotCount: 4,
      storyboardPrompt: '镜头1 正面；镜头2 侧面；镜头3 背面；镜头4 袖口。',
      videoPrompt: '图片1是分镜故事板；图片2是服饰参考图；图片3是角色（模特）参考图；图片4是场景参考图。镜头1正面；镜头2侧面；镜头3背面；镜头4袖口。',
      imageSettings: { model: 'gpt-image-2', aspectRatio: '16:9', resolution: '2K' },
      videoSettings: { model: 'seedance-2-mini', duration: 10, aspectRatio: '16:9', resolution: '720p', generateAudio: true },
    })

    expect(resultIds).toHaveLength(2)
    const image = store.nodes.find((node) => node.id === resultIds[0])
    expect(image.data).toEqual(expect.objectContaining({ storyboardTemplateId: 'apparel-showcase', storyboardShotCount: 4, storyboardRequiresRegistration: true, prompt: '镜头1 正面；镜头2 侧面；镜头3 背面；镜头4 袖口。' }))
    expect(store.edges.filter((edge) => edge.target === resultIds[0])).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: storyboardId }),
      expect.objectContaining({ source: garmentId }),
      expect.objectContaining({ source: modelId }),
      expect.objectContaining({ source: sceneId }),
    ]))
    expect(store.nodes.find((node) => node.id === resultIds[1]).data).toEqual(expect.objectContaining({ model: 'seedance-2-mini', duration: 10, generateAudio: true, prompt: expect.stringContaining('图片1是分镜故事板') }))
    expect(store.edges).toEqual(expect.arrayContaining([expect.objectContaining({ source: resultIds[0], target: resultIds[1] }), expect.objectContaining({ source: modelId, target: resultIds[1] })]))
  })
})
