import { useModelCapabilitiesStore } from '../modelCapabilities'
import { createCanvasEdge } from './sharedActions'

export function createApparelChain(position, sourceId) {
  if (sourceId) return { handled: false }
  const imageId = this.addNode('image', { x: position.x - 460, y: position.y + 3 })
  const image = this.nodes.find((node) => node.id === imageId)
  image.data = { ...image.data, title: '服饰参考图', assetSource: 'upload', resourceType: 'garment' }
  return { handled: true, id: this.addNode('apparel', position, imageId) }
}

export function createOutfitChain(position, sourceId) {
  if (sourceId) return { handled: false }
  const apparelId = this.addNode('apparel', { x: position.x - 500, y: position.y - 170 })
  const modelId = this.addNode('image', { x: position.x - 500, y: position.y + 190 })
  const model = this.nodes.find((node) => node.id === modelId)
  model.data = { ...model.data, title: '模特参考图', assetSource: 'upload', resourceType: 'model' }
  const outfitId = this.addNode('outfit', position, apparelId)
  const apparelEdge = this.edges.find((edge) => edge.source === apparelId && edge.target === outfitId)
  apparelEdge.targetHandle = 'apparel'
  this.edges.push(createCanvasEdge(`edge-${crypto.randomUUID()}`, modelId, outfitId, 'model'))
  this.selectNodes([outfitId])
  return { handled: true, id: outfitId }
}

export function createApparelStoryboardChain(position, sourceId, skipStoryboardInputs) {
  const source = this.nodes.find((node) => node.id === sourceId)
  if (skipStoryboardInputs || (sourceId && source?.type !== 'apparel')) return { handled: false }
  const apparelId = source?.type === 'apparel'
    ? source.id
    : this.addNode('apparel', { x: position.x - 520, y: position.y - 220 })
  const roleId = this.addNode('image', { x: position.x - 520, y: position.y + 120 })
  const role = this.nodes.find((node) => node.id === roleId)
  role.data = { ...role.data, title: '角色节点', assetSource: 'upload', resourceType: 'model', inputRole: 'role' }
  const sceneId = this.addNode('image', { x: position.x - 520, y: position.y + 390 })
  const scene = this.nodes.find((node) => node.id === sceneId)
  scene.data = { ...scene.data, title: '场景节点', assetSource: 'upload', resourceType: 'asset', inputRole: 'scene' }
  const storyboardId = this.addNode('apparel_storyboard', position, apparelId, true)
  const apparelEdge = this.edges.find((edge) => edge.source === apparelId && edge.target === storyboardId)
  if (apparelEdge) apparelEdge.targetHandle = 'apparel'
  this.edges.push(
    createCanvasEdge(`edge-${crypto.randomUUID()}`, roleId, storyboardId, 'model'),
    createCanvasEdge(`edge-${crypto.randomUUID()}`, sceneId, storyboardId, 'scene'),
  )
  this.selectNodes([storyboardId])
  return { handled: true, id: storyboardId }
}

export const apparelActions = {
  addApparelStoryboardNodes(plannerId, garmentId, modelId, sceneId, plan, settings = {}) {
    const planner = this.nodes.find((node) => node.id === plannerId)
    if (!planner || !plan?.storyboardPrompt?.trim() || !plan.videoPrompt?.trim()) return []
    const capabilities = useModelCapabilitiesStore()
    const defaultImageModel = capabilities.defaultImageModel
    const defaultVideoModel = capabilities.defaultVideoModel
    const imageSettings = settings.imageSettings || {
      model: defaultImageModel.id,
      aspectRatio: planner.data.videoAspectRatio,
      resolution: defaultImageModel.resolutions.includes('2K') ? '2K' : defaultImageModel.defaultResolution,
    }
    const videoSettings = settings.videoSettings || {
      model: planner.data.videoModel || defaultVideoModel.id,
      duration: planner.data.duration || defaultVideoModel.defaultDuration,
      aspectRatio: planner.data.videoAspectRatio || defaultVideoModel.defaultAspectRatio,
      resolution: planner.data.videoResolution || defaultVideoModel.defaultResolution,
      generateAudio: true,
    }
    const imageId = this.addNode('image', { x: planner.position.x + 560, y: planner.position.y })
    const image = this.nodes.find((node) => node.id === imageId)
    image.data = {
      ...image.data,
      title: `${plan.title || '服饰展示'} · 故事板`,
      storyboardSourceId: plannerId,
      storyboardTemplateId: plan.templateId,
      storyboardTemplateLabel: plan.title,
      storyboardDuration: plan.duration,
      storyboardVideoAspectRatio: videoSettings.aspectRatio,
      storyboardShotCount: plan.shotCount,
      storyboardReferenceOrder: ['服饰参考图', '角色节点', '场景节点'],
      storyboardRequiresRegistration: true,
      videoPrompt: plan.videoPrompt,
      prompt: plan.storyboardPrompt,
      promptParts: [{ type: 'text', value: plan.storyboardPrompt }],
      ...imageSettings,
    }
    this.addEdge({ source: plannerId, target: imageId })
    ;[garmentId, modelId, sceneId].filter(Boolean).forEach((source) => this.addEdge({ source, target: imageId }))
    const videoId = this.addNode('video', { x: planner.position.x + 980, y: planner.position.y }, imageId)
    const video = this.nodes.find((node) => node.id === videoId)
    video.data = {
      ...video.data,
      title: `${plan.title || '服饰展示'} · 视频`,
      storyboardSourceId: plannerId,
      storyboardImageId: imageId,
      storyboardTemplateId: plan.templateId,
      storyboardTemplateLabel: plan.title,
      storyboardDuration: plan.duration,
      storyboardShotCount: plan.shotCount,
      storyboardReferenceOrder: ['分镜故事板', '服饰参考图', '角色节点', '场景节点'],
      videoPrompt: plan.videoPrompt,
      prompt: plan.videoPrompt,
      promptParts: [{ type: 'text', value: plan.videoPrompt }],
      ...videoSettings,
    }
    ;[garmentId, modelId, sceneId].filter(Boolean).forEach((source) => this.addEdge({ source, target: videoId }))
    planner.data = {
      ...planner.data,
      generatedNodeIds: [imageId, videoId],
      storyboardImageId: imageId,
      storyboardVideoId: videoId,
      storyboardShotCount: plan.shotCount,
      storyboardPrompt: plan.storyboardPrompt,
      videoPrompt: plan.videoPrompt,
      videoModel: videoSettings.model,
      duration: videoSettings.duration,
      videoAspectRatio: videoSettings.aspectRatio,
      videoResolution: videoSettings.resolution,
      generateAudio: videoSettings.generateAudio,
    }
    this.selectNodes([imageId])
    return [imageId, videoId]
  },

  addOutfitStoryboardNodes(plannerId, outfitId, plans, settings) {
    const planner = this.nodes.find((node) => node.id === plannerId)
    if (!planner || !plans?.segments?.length) return []
    const outfit = this.nodes.find((node) => node.id === outfitId)
    const board = outfit?.data.outfitBoardAsset
      ? { url: outfit.data.outfitBoardAsset, assetId: outfit.data.outfitBoardAssetId || null }
      : null
    const segmentNodeIds = []
    let previousVideoId = null
    plans.segments.forEach((segment, index) => {
      const segmentIndex = index + 1
      const imageId = this.addNode('image', {
        x: planner.position.x + 560 + index * 900,
        y: planner.position.y,
      })
      const image = this.nodes.find((node) => node.id === imageId)
      image.data = {
        ...image.data,
        title: `${plans.title || '服饰分镜'} ${segmentIndex} · 分镜`,
        storyboardSourceId: plannerId,
        storyboardTemplateId: plans.templateId,
        storyboardTemplateLabel: plans.title,
        storyboardGlobalScript: plans.globalScript,
        storyboardSegmentIndex: segmentIndex,
        storyboardSegmentCount: plans.segments.length,
        storyboardDuration: 15,
        storyboardVideoAspectRatio: planner.data.videoAspectRatio,
        storyboardShotCount: 6,
        storyboardOutfitBoard: board,
        storyboardRequiresRegistration: true,
        storyboardContinuityMode: segment.continuityMode,
        storyboardPlotGoal: segment.plotGoal,
        storyboardOpeningState: segment.openingState,
        storyboardEndingState: segment.endingState,
        videoPrompt: segment.videoPrompt,
        prompt: segment.prompt,
        promptParts: [{ type: 'text', value: segment.prompt }],
        segmentLocked: segmentIndex > 1,
        ...settings,
      }
      this.addEdge({ source: plannerId, target: imageId })
      this.addEdge({ source: outfitId, target: imageId })
      const videoId = this.addNode('video', {
        x: planner.position.x + 1010 + index * 900,
        y: planner.position.y,
      }, imageId)
      const video = this.nodes.find((node) => node.id === videoId)
      video.data = {
        ...video.data,
        title: `${plans.title || '服饰分镜'} ${segmentIndex} · 视频`,
        storyboardSourceId: plannerId,
        storyboardImageId: imageId,
        storyboardTemplateId: plans.templateId,
        storyboardTemplateLabel: plans.title,
        storyboardGlobalScript: plans.globalScript,
        storyboardSegmentIndex: segmentIndex,
        storyboardSegmentCount: plans.segments.length,
        storyboardContinuityMode: segment.continuityMode,
        storyboardPlotGoal: segment.plotGoal,
        storyboardOpeningState: segment.openingState,
        storyboardEndingState: segment.endingState,
        storyboardOutfitBoard: board,
        storyboardRequiresRegistration: true,
        storyboardDuration: 15,
        videoPrompt: segment.videoPrompt,
        prompt: segment.videoPrompt,
        promptParts: [{ type: 'text', value: segment.videoPrompt }],
        segmentLocked: true,
      }
      if (segment.continuityMode === 'extend' && previousVideoId) {
        this.addEdge({ source: previousVideoId, target: videoId })
      }
      segmentNodeIds.push({ segmentIndex, imageId, videoId })
      previousVideoId = videoId
    })
    planner.data = {
      ...planner.data,
      storyboardOutfitBoard: board,
      globalScript: plans.globalScript,
      segmentNodeIds,
      generatedNodeIds: segmentNodeIds.flatMap(({ imageId, videoId }) => [imageId, videoId]),
    }
    this.selectNodes([segmentNodeIds[0].imageId])
    return planner.data.generatedNodeIds
  },

  addOutfitVisualNodes(outfitId, garmentId, modelId, plans, settings) {
    const outfit = this.nodes.find((node) => node.id === outfitId)
    if (!outfit || !plans.length) return []
    const columns = Math.min(3, plans.length)
    const ids = plans.map((plan, index) => {
      const id = this.addNode('image', {
        x: outfit.position.x + 500 + (index % columns) * 440,
        y: outfit.position.y + Math.floor(index / columns) * 340,
      })
      const node = this.nodes.find((item) => item.id === id)
      node.data = {
        ...node.data,
        title: plan.label,
        outfitSourceId: outfitId,
        outfitMaterialId: plan.id,
        outfitMaterialCategory: plan.category,
        outfitMaterialCategoryLabel: plan.categoryLabel,
        resourceType: 'outfit-material',
        prompt: plan.prompt,
        promptParts: [{ type: 'text', value: plan.prompt }],
        ...settings,
      }
      this.addEdge({ source: outfitId, target: id })
      this.addEdge({ source: garmentId, target: id })
      this.addEdge({ source: modelId, target: id })
      return id
    })
    this.selectNodes(ids.slice(0, 1))
    return ids
  },
}
