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

async function createWorkflow() {
  const store = useCanvasStore()
  await store.loadWorkspace({
    id: 'workspace-1', version: 1, workspace_type: 'ecommerce',
    canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
  })
  const outfitId = store.addEcommerceWorkflow('apparel', { x: 1020, y: 300 })
  return { store, outfitId }
}

describe('canvas apparel video workflow', () => {
  it('creates only garment, apparel recognition and outfit nodes', async () => {
    const { store, outfitId } = await createWorkflow()
    const workflowId = store.nodes.find((node) => node.id === outfitId).data.workflowId

    expect(outfitId).toBe('outfit-3')
    expect(store.nodes).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'image-1', data: expect.objectContaining({ title: '服饰参考图', resourceType: 'garment' }) }),
      expect.objectContaining({ id: 'apparel-2', type: 'apparel' }),
      expect.objectContaining({ id: outfitId, type: 'outfit', data: expect.objectContaining({ workflowRoot: true, modelSource: 'default', sceneSource: 'default' }) }),
    ]))
    expect(store.nodes).toHaveLength(3)
    expect(store.nodes.every((node) => node.data.workflowId === workflowId)).toBe(true)
    expect(store.nodes.some((node) => node.type === 'apparel_storyboard')).toBe(false)
    expect(store.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: 'image-1', target: 'apparel-2', workflowId }),
      expect.objectContaining({ source: 'apparel-2', target: outfitId, targetHandle: 'apparel', workflowId }),
    ]))
  })

  it('creates one try-on reference with only outfit and garment inputs', async () => {
    const { store, outfitId } = await createWorkflow()
    const resultId = store.addOutfitVisualNode(outfitId, 'image-1', '正面全身试穿定妆图', {
      model: 'gpt-image-2', aspectRatio: '3:4', resolution: '2K',
    })

    expect(resultId).toBe('image-4')
    expect(store.nodes.find((node) => node.id === resultId).data).toEqual(expect.objectContaining({
      title: '试穿定妆图', outfitSourceId: outfitId, resourceType: 'outfit-reference', requiresPrivateRegistration: true, prompt: '正面全身试穿定妆图',
    }))
    expect(store.edges.filter((edge) => edge.target === resultId)).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: outfitId }),
      expect.objectContaining({ source: 'image-1' }),
    ]))
    expect(store.edges.filter((edge) => edge.target === resultId)).toHaveLength(2)
  })

  it('creates a video with fixed try-on and garment references', async () => {
    const { store, outfitId } = await createWorkflow()
    const referenceId = store.addOutfitVisualNode(outfitId, 'image-1', '正面全身试穿定妆图', {})
    const videoId = store.addOutfitVideoNode(outfitId, referenceId, 'image-1', '真实手机实拍服饰展示', {
      model: 'seedance-2-mini', aspectRatio: '9:16', duration: 15, resolution: '720p', generateAudio: false,
    })

    expect(store.nodes.find((node) => node.id === videoId).data).toEqual(expect.objectContaining({
      outfitReferenceOrder: ['定妆图', '服饰原图'], generateAudio: false,
    }))
    expect(store.edges.filter((edge) => edge.target === videoId).map((edge) => edge.source)).toEqual([referenceId, 'image-1'])
  })
})
