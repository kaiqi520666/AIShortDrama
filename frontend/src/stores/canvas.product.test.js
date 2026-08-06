import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { seedModelCapabilities } from '../test/modelCapabilities'
import { useCanvasStore } from './canvas'

beforeEach(() => {
  setActivePinia(createPinia())
  seedModelCapabilities()
})

describe('canvas product workflows', () => {
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
      textModel: 'gpt-5.6-sol',
      imageModel: 'gpt-image-2',
      items: expect.arrayContaining([expect.objectContaining({ id: 'white-bg', enabled: true })]),
      prompt: '',
    }))
    expect(store.edges).toEqual([
      expect.objectContaining({ source: 'image-1', target: productId }),
    ])
  })

  it('creates one editable UGC storyboard image node', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'ecommerce',
      canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })
    const productId = store.addNode('product', { x: 0, y: 0 })
    const storyboardId = store.addNode('product_storyboard', { x: 500, y: 0 }, productId)
    expect(store.nodes.find((node) => node.id === storyboardId).data.duration).toBe(30)
    store.nodes.find((node) => node.id === storyboardId).data.duration = 8
    store.nodes.find((node) => node.id === storyboardId).data.characterReferences = [{
      id: 'character-1', name: '虚拟角色', url: 'https://example.com/character.png', assetUrl: 'asset://pa_test',
    }]
    store.nodes.find((node) => node.id === storyboardId).data.productReferences = [
      { id: 'asset-1', name: '商品正面', url: 'https://example.com/product.png' },
    ]
    const ids = store.addProductStoryboardNodes(storyboardId, productId, [
      { id: 'ugc-seeding', label: 'UGC 种草', prompt: '四格种草分镜板', videoPrompt: '参考图片1生成种草视频' },
    ], { model: 'gpt-image-2', aspectRatio: '9:16', resolution: '2K' })

    expect(ids).toEqual(['image-4'])
    expect(store.nodes.find((node) => node.id === ids[0]).data).toEqual(expect.objectContaining({
      title: 'UGC 种草分镜板',
      storyboardSourceId: storyboardId,
      storyboardTemplateId: 'ugc-seeding',
      storyboardDuration: 8,
      storyboardVideoAspectRatio: '9:16',
      storyboardShotCount: 3,
      storyboardCharacterReferences: [expect.objectContaining({ id: 'character-1', assetUrl: 'asset://pa_test' })],
      videoPrompt: '参考图片1生成种草视频',
      prompt: '四格种草分镜板',
      aspectRatio: '9:16',
      resolution: '2K',
    }))
    expect(store.edges.filter((edge) => ids.includes(edge.target))).toHaveLength(2)
    expect(store.nodes.find((node) => node.id === ids[0]).data.storyboardProductReferences).toEqual([
      { id: 'asset-1', name: '商品正面', url: 'https://example.com/product.png' },
    ])

    const storyboardImage = store.nodes.find((node) => node.id === ids[0])
    storyboardImage.data = { ...storyboardImage.data, asset: 'https://example.com/storyboard.png', status: 'ready' }
    const videoId = store.addStoryboardVideoNode(ids[0])
    expect(videoId).toBe('video-5')
    expect(store.nodes.find((node) => node.id === videoId).data).toEqual(expect.objectContaining({
      title: 'UGC 种草视频',
      storyboardImageId: ids[0],
      prompt: '参考图片1生成种草视频',
      duration: 8,
      aspectRatio: '9:16',
      resolution: '720p',
      storyboardCharacterReferences: [expect.objectContaining({ id: 'character-1', assetUrl: 'asset://pa_test' })],
      storyboardProductReferences: [{ id: 'asset-1', name: '商品正面', url: 'https://example.com/product.png' }],
    }))
    expect(store.edges).toContainEqual(expect.objectContaining({ source: ids[0], target: videoId }))
    expect(store.addStoryboardVideoNode(ids[0])).toBe(videoId)
  })

  it('preserves saved product storyboard settings during migration', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1',
      version: 1,
      workspace_type: 'ecommerce',
      canvas: {
        nodes: [{
          id: 'product_storyboard-1',
          type: 'product_storyboard',
          position: { x: 0, y: 0 },
          data: {
            textModel: 'qwen3.7',
            templateId: 'tvc',
            templates: [{ id: 'tvc', label: 'TVC 广告', enabled: true }],
          },
        }],
        edges: [],
        groups: [],
        sequence: 2,
      },
    })

    expect(store.nodes[0].data).toEqual(expect.objectContaining({
      textModel: 'qwen3.7',
      templateId: 'tvc',
      templates: [{ id: 'tvc', label: 'TVC 广告', enabled: true }],
    }))
  })

  it('creates locked storyboard and video segments that unlock in sequence', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1', version: 1, workspace_type: 'ecommerce', canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })
    const productId = store.addNode('product', { x: 0, y: 0 })
    const storyboardId = store.addNode('product_storyboard', { x: 500, y: 0 }, productId)
    const plan = {
      templateId: 'ugc-seeding', title: 'UGC 种草', globalScript: '全局脚本', totalDuration: 30,
      segments: [
        { segmentIndex: 1, duration: 15, plotGoal: '开场', openingState: '开始', endingState: '拿起', continuityMode: 'cut', prompt: '分镜1', videoPrompt: '视频1' },
        { segmentIndex: 2, duration: 15, plotGoal: '结果', openingState: '拿起', endingState: '展示', continuityMode: 'extend', prompt: '分镜2', videoPrompt: '视频2' },
      ],
    }
    const ids = store.addProductStoryboardNodes(storyboardId, productId, plan, { model: 'gpt-image-2', aspectRatio: '9:16', resolution: '2K' })
    const [image1, video1, image2, video2] = ids.map((id) => store.nodes.find((node) => node.id === id))

    expect(ids).toHaveLength(4)
    expect(image1.data.segmentLocked).toBe(false)
    expect(video1.data.segmentLocked).toBe(true)
    expect(image2.data.segmentLocked).toBe(true)
    expect(video2.data.segmentLocked).toBe(true)
    expect(store.edges).toContainEqual(expect.objectContaining({ source: video1.id, target: video2.id }))

    image1.data.status = 'ready'
    image1.data.asset = 'https://example.com/storyboard-1.png'
    store.unlockStoryboardVideo(image1.id)
    expect(video1.data.segmentLocked).toBe(false)
    video1.data.status = 'ready'
    expect(store.confirmStoryboardSegment(video1.id)).toBe(true)
    expect(image2.data.segmentLocked).toBe(false)
    expect(image2.data).not.toHaveProperty('continuityLastFrameUrl')

    image2.data.asset = 'https://example.com/storyboard-2.png'
    store.invalidateStoryboardFrom(image2.id)
    expect(image2.data.asset).toBe('')
    expect(image2.data.segmentLocked).toBe(false)
    expect(video2.data.segmentLocked).toBe(true)
    expect(image2.data.storyboardHistory).toHaveLength(1)
  })

  it('syncs changed storyboard references to generated image and video nodes', async () => {
    const store = useCanvasStore()
    await store.loadWorkspace({
      id: 'workspace-1', version: 1, workspace_type: 'ecommerce', canvas: { nodes: [], edges: [], groups: [], sequence: 1 },
    })
    const productId = store.addNode('product', { x: 0, y: 0 })
    const storyboardId = store.addNode('product_storyboard', { x: 500, y: 0 }, productId)
    const planner = store.nodes.find((node) => node.id === storyboardId)
    planner.data.productReferences = [{ id: 'old-product', name: '旧商品图', url: 'https://example.com/old-product.png' }]
    planner.data.characterReferences = [{ id: 'old-character', name: '旧角色', url: 'https://example.com/old-character.png' }]
    const [imageId] = store.addProductStoryboardNodes(storyboardId, productId, [
      { id: 'ugc-seeding', label: 'UGC 种草', prompt: '分镜板', videoPrompt: '视频提示词' },
    ], { model: 'gpt-image-2', aspectRatio: '9:16', resolution: '2K' })
    const image = store.nodes.find((node) => node.id === imageId)
    image.data.asset = 'https://example.com/storyboard.png'
    const videoId = store.addStoryboardVideoNode(imageId)
    const nextReferences = [{ id: 'new-product', name: '新商品图', url: 'https://example.com/new-product.png' }]
    const nextCharacters = [{ id: 'new-character', name: '新角色', url: 'https://example.com/new-character.png', assetUrl: 'asset://new-character' }]

    store.syncProductStoryboardReferences(storyboardId, nextReferences, nextCharacters)

    expect(store.nodes.filter((node) => [imageId, videoId].includes(node.id)).map((node) => node.data)).toEqual([
      expect.objectContaining({ storyboardProductReferences: nextReferences, storyboardCharacterReferences: nextCharacters }),
      expect.objectContaining({ storyboardProductReferences: nextReferences, storyboardCharacterReferences: nextCharacters }),
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
    const secondReferenceId = store.addNode('image', { x: 0, y: 380 })
    store.nodes.find((node) => node.id === secondReferenceId).data.asset = 'https://example.com/product-side.png'

    const ids = store.addProductVisualNodes(productId, productId, [referenceId, secondReferenceId], [
      { id: 'white-bg', label: '白底图', prompt: '纯白背景商品图' },
      { id: 'first-screen', label: '首屏主视觉', prompt: '首屏主视觉商品图' },
    ], { model: 'gpt-image-2', aspectRatio: '1:1', resolution: '1K' })

    expect(ids).toEqual(['image-4', 'image-5'])
    expect(store.nodes.find((node) => node.id === ids[0]).data).toEqual(expect.objectContaining({
      title: '白底图', prompt: '纯白背景商品图', model: 'gpt-image-2', aspectRatio: '1:1', resolution: '1K',
    }))
    expect(store.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: referenceId, target: ids[0] }),
      expect.objectContaining({ source: secondReferenceId, target: ids[0] }),
      expect.objectContaining({ source: productId, target: ids[0] }),
      expect.objectContaining({ source: referenceId, target: ids[1] }),
      expect.objectContaining({ source: secondReferenceId, target: ids[1] }),
      expect.objectContaining({ source: productId, target: ids[1] }),
    ]))
    expect(store.edges.filter((edge) => ids.includes(edge.target))).toHaveLength(6)
  })
})
