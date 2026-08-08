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
      expect.objectContaining({ id: 'apparel-2', type: 'apparel', data: expect.objectContaining({ title: '服饰识别 2', items: [] }) }),
      expect.objectContaining({ id: 'image-3', data: expect.objectContaining({ title: '模特参考图', assetSource: 'upload', resourceType: 'model' }) }),
      expect.objectContaining({ id: outfitId, type: 'outfit', data: expect.objectContaining({ title: '模特试穿 4', textModel: 'gpt-5.6-sol', imageModel: 'gpt-image-2', aspectRatio: '9:16', resolution: '1K', templateVersion: 2, customRequirement: '', generatedNodeIds: [] }) }),
    ]))
    expect(store.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: 'image-1', target: 'apparel-2' }),
      expect.objectContaining({ source: 'apparel-2', target: outfitId, targetHandle: 'apparel' }),
      expect.objectContaining({ source: 'image-3', target: outfitId, targetHandle: 'model' }),
    ]))
    expect(store.nodes.filter((node) => node.selected).map((node) => node.id)).toEqual([outfitId])
  })

  it('creates apparel storyboard inputs for model try-on and optional scene', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })

    const storyboardId = store.addNode('apparel_storyboard', { x: 900, y: 300 })

    expect(storyboardId).toBe('apparel_storyboard-6')
    expect(store.nodes).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'apparel-2' }),
      expect.objectContaining({ id: 'image-3', data: expect.objectContaining({ title: '模特参考图', resourceType: 'model' }) }),
      expect.objectContaining({ id: 'outfit-4', data: expect.objectContaining({ title: '模特试穿 4' }) }),
      expect.objectContaining({ id: 'image-5', data: expect.objectContaining({ title: '场景节点', inputRole: 'scene' }) }),
      expect.objectContaining({ id: storyboardId }),
    ]))
    expect(store.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: 'outfit-4', target: storyboardId, targetHandle: 'outfit' }),
      expect.objectContaining({ source: 'image-5', target: storyboardId, targetHandle: 'scene' }),
    ]))
    expect(store.nodes.filter((node) => node.selected).map((node) => node.id)).toEqual([storyboardId])
  })

  it('creates one try-on reference image with shared inputs', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })
    const outfitId = store.addNode('outfit', { x: 500, y: 300 })
    const resultId = store.addOutfitVisualNode(outfitId, 'image-1', 'image-3', '正面全身试穿定妆图', {
      model: 'gpt-image-2', aspectRatio: '3:4', resolution: '2K',
    })

    expect(resultId).toBe('image-5')
    expect(store.nodes.find((node) => node.id === resultId).data).toEqual(expect.objectContaining({
      title: '试穿定妆图', outfitSourceId: outfitId, resourceType: 'outfit-reference', status: 'empty', prompt: '正面全身试穿定妆图', model: 'gpt-image-2', aspectRatio: '3:4', resolution: '2K',
    }))
    expect(store.edges.filter((edge) => edge.target === resultId)).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: outfitId }),
      expect.objectContaining({ source: 'image-1' }),
      expect.objectContaining({ source: 'image-3' }),
    ]))
    expect(store.edges.filter((edge) => edge.target === resultId)).toHaveLength(3)
    expect(store.nodes.filter((node) => node.selected).map((node) => node.id)).toEqual([resultId])
  })

  it('creates multi-segment apparel storyboard nodes with extend continuity', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })
    const storyboardId = store.addNode('apparel_storyboard', { x: 1000, y: 300 })
    const sceneId = 'image-5'
    const outfitReferenceId = store.addNode('image', { x: 500, y: 100 })
    store.nodes.find((node) => node.id === outfitReferenceId).data = { resourceType: 'outfit-reference', asset: 'https://example.com/try-on.png', assetId: 'try-on-asset' }
    const segment = (segmentIndex, continuityMode) => ({ segmentIndex, duration: 15, shotCount: 6, plotGoal: `目标${segmentIndex}`, openingState: '开头', endingState: '结尾', continuityMode, prompt: `分镜${segmentIndex}`, videoPrompt: `视频${segmentIndex}` })
    const resultIds = store.addOutfitStoryboardNodes(storyboardId, outfitReferenceId, { url: 'https://example.com/try-on.png', assetId: 'try-on-asset' }, sceneId, {
      templateId: 'apparel-showcase', title: '服饰展示', globalScript: '整体到细节', segments: [segment(1, 'cut'), segment(2, 'extend')],
    }, { model: 'gpt-image-2', aspectRatio: '16:9', resolution: '2K' })

    expect(resultIds).toHaveLength(4)
    expect(store.nodes.find((node) => node.id === resultIds[0]).data).toEqual(expect.objectContaining({ storyboardTemplateId: 'apparel-showcase', storyboardTemplateKey: 'apparel_showcase', storyboardShotCount: 6, prompt: '分镜1' }))
    expect(store.nodes.find((node) => node.id === resultIds[2]).data).toEqual(expect.objectContaining({ storyboardContinuityMode: 'extend', segmentLocked: true }))
    expect(store.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: sceneId, target: resultIds[0] }),
      expect.objectContaining({ source: outfitReferenceId, target: resultIds[0] }),
      expect.objectContaining({ source: resultIds[1], target: resultIds[3] }),
    ]))
  })
})
