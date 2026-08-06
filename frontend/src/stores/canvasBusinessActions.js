import {
  buildStoryboardReferenceManifest,
  normalizeStoryboardCharacters,
  storyboardShotCount,
} from '../config/canvas/productStoryboard'
import { defaultVideoModel } from '../config/videoModels'

export const createCanvasEdge = (id, source, target, targetHandle) => ({
  id,
  source,
  target,
  ...(targetHandle ? { targetHandle } : {}),
  type: 'cinematic',
})

export function storyboardVideoData(source) {
  const prompt = source?.type === 'image' ? source.data.videoPrompt?.trim() : ''
  if (!prompt) return null
  return {
    storyboardImageId: source.id,
    prompt,
    promptParts: [{ type: 'text', value: prompt }],
    model: defaultVideoModel.id,
    duration: source.data.storyboardDuration || defaultVideoModel.defaultDuration,
    aspectRatio: source.data.storyboardVideoAspectRatio || defaultVideoModel.defaultAspectRatio,
    resolution: defaultVideoModel.defaultResolution,
    generateAudio: true,
    storyboardCharacterReferences: normalizeStoryboardCharacters(source.data.storyboardCharacterReferences),
    storyboardProductReferences: source.data.storyboardProductReferences || [],
  }
}

export function createBusinessNodeChain(type, position, sourceId, skipStoryboardInputs) {
  const source = this.nodes.find((node) => node.id === sourceId)
  if (type === 'apparel' && !sourceId) {
    const imageId = this.addNode('image', { x: position.x - 460, y: position.y + 3 })
    const image = this.nodes.find((node) => node.id === imageId)
    image.data = { ...image.data, title: '服饰参考图', assetSource: 'upload', resourceType: 'garment' }
    return { handled: true, id: this.addNode(type, position, imageId) }
  }
  if (type === 'outfit' && !sourceId) {
    const apparelId = this.addNode('apparel', { x: position.x - 500, y: position.y - 170 })
    const modelId = this.addNode('image', { x: position.x - 500, y: position.y + 190 })
    const model = this.nodes.find((node) => node.id === modelId)
    model.data = { ...model.data, title: '模特参考图', assetSource: 'upload', resourceType: 'model' }
    const outfitId = this.addNode(type, position, apparelId)
    const apparelEdge = this.edges.find((edge) => edge.source === apparelId && edge.target === outfitId)
    apparelEdge.targetHandle = 'apparel'
    this.edges.push(createCanvasEdge(`edge-${crypto.randomUUID()}`, modelId, outfitId, 'model'))
    this.selectNodes([outfitId])
    return { handled: true, id: outfitId }
  }
  if (type === 'apparel_storyboard' && !skipStoryboardInputs && (!sourceId || source?.type === 'apparel')) {
    const apparelId = source?.type === 'apparel'
      ? source.id
      : this.addNode('apparel', { x: position.x - 520, y: position.y - 220 })
    const roleId = this.addNode('image', { x: position.x - 520, y: position.y + 120 })
    const role = this.nodes.find((node) => node.id === roleId)
    role.data = { ...role.data, title: '角色节点', assetSource: 'upload', resourceType: 'model', inputRole: 'role' }
    const sceneId = this.addNode('image', { x: position.x - 520, y: position.y + 390 })
    const scene = this.nodes.find((node) => node.id === sceneId)
    scene.data = { ...scene.data, title: '场景节点', assetSource: 'upload', resourceType: 'asset', inputRole: 'scene' }
    const storyboardId = this.addNode(type, position, apparelId, true)
    const apparelEdge = this.edges.find((edge) => edge.source === apparelId && edge.target === storyboardId)
    if (apparelEdge) apparelEdge.targetHandle = 'apparel'
    this.edges.push(
      createCanvasEdge(`edge-${crypto.randomUUID()}`, roleId, storyboardId, 'model'),
      createCanvasEdge(`edge-${crypto.randomUUID()}`, sceneId, storyboardId, 'scene'),
    )
    this.selectNodes([storyboardId])
    return { handled: true, id: storyboardId }
  }
  if (type === 'product' && !sourceId) {
    const imageId = this.addNode('image', { x: position.x - 460, y: position.y + 3 })
    const image = this.nodes.find((node) => node.id === imageId)
    image.data = { ...image.data, title: '商品参考图', assetSource: 'upload' }
    return { handled: true, id: this.addNode(type, position, imageId) }
  }
  if (type === 'character' && (!sourceId || source?.type === 'world')) {
    const imageId = this.addNode('image', { x: position.x - 460, y: position.y + 210 })
    const image = this.nodes.find((node) => node.id === imageId)
    image.data = { ...image.data, title: '角色参考图', assetSource: 'upload', resourceType: 'character' }
    const characterId = this.addNode(type, position, imageId)
    if (source?.type === 'world') {
      this.edges.push(createCanvasEdge(`edge-${crypto.randomUUID()}`, source.id, characterId, 'world'))
    }
    this.selectNodes([characterId])
    return { handled: true, id: characterId }
  }
  return { handled: false }
}

export const canvasBusinessActions = {
  addProductVisualNodes(plannerId, productId, referenceIds, plans, settings) {
    const planner = this.nodes.find((node) => node.id === plannerId)
    if (!planner || !plans.length) return []
    const references = (Array.isArray(referenceIds) ? referenceIds : [referenceIds]).filter(Boolean)
    const columns = Math.min(3, plans.length)
    const ids = plans.map((plan, index) => {
      const id = this.addNode('image', {
        x: planner.position.x + 500 + (index % columns) * 440,
        y: planner.position.y + Math.floor(index / columns) * 340,
      })
      const node = this.nodes.find((item) => item.id === id)
      node.data = {
        ...node.data,
        title: plan.label,
        prompt: plan.prompt,
        promptParts: [{ type: 'text', value: plan.prompt }],
        model: settings.model,
        aspectRatio: settings.aspectRatio,
        resolution: settings.resolution,
      }
      this.addEdge({ source: plannerId, target: id })
      references.forEach((referenceId) => this.addEdge({ source: referenceId, target: id }))
      this.addEdge({ source: productId, target: id })
      return id
    })
    this.selectNodes(ids.slice(0, 1))
    return ids
  },

  addProductStoryboardNodes(plannerId, productId, plans, settings) {
    const planner = this.nodes.find((node) => node.id === plannerId)
    if (!planner) return []
    const referenceManifest = buildStoryboardReferenceManifest(
      planner.data.characterReferences,
      planner.data.productReferences,
    )
    if (plans?.segments?.length) {
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
          title: `${plans.title || '商品分镜'} ${segmentIndex} · 分镜`,
          storyboardSourceId: plannerId,
          storyboardTemplateId: 'ugc-seeding',
          storyboardTemplateLabel: plans.title,
          storyboardGlobalScript: plans.globalScript,
          storyboardSegmentIndex: segmentIndex,
          storyboardSegmentCount: plans.segments.length,
          storyboardDuration: 15,
          storyboardVideoAspectRatio: planner.data.videoAspectRatio,
          storyboardShotCount: 6,
          storyboardProductReferences: referenceManifest.products,
          storyboardCharacterReferences: referenceManifest.characters,
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
        this.addEdge({ source: productId, target: imageId })
        const videoId = this.addNode('video', {
          x: planner.position.x + 1010 + index * 900,
          y: planner.position.y,
        }, imageId)
        const video = this.nodes.find((node) => node.id === videoId)
        video.data = {
          ...video.data,
          title: `${plans.title || '商品分镜'} ${segmentIndex} · 视频`,
          storyboardSourceId: plannerId,
          storyboardImageId: imageId,
          storyboardTemplateId: 'ugc-seeding',
          storyboardTemplateLabel: plans.title,
          storyboardGlobalScript: plans.globalScript,
          storyboardSegmentIndex: segmentIndex,
          storyboardSegmentCount: plans.segments.length,
          storyboardContinuityMode: segment.continuityMode,
          storyboardPlotGoal: segment.plotGoal,
          storyboardOpeningState: segment.openingState,
          storyboardEndingState: segment.endingState,
          storyboardCharacterReferences: referenceManifest.characters,
          storyboardProductReferences: referenceManifest.products,
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
        globalScript: plans.globalScript,
        segmentNodeIds,
        generatedNodeIds: segmentNodeIds.flatMap(({ imageId, videoId }) => [imageId, videoId]),
      }
      this.selectNodes([segmentNodeIds[0].imageId])
      return planner.data.generatedNodeIds
    }
    if (!plans?.length) return []
    const columns = Math.min(3, plans.length)
    const ids = plans.map((plan, index) => {
      const id = this.addNode('image', {
        x: planner.position.x + 500 + (index % columns) * 440,
        y: planner.position.y + Math.floor(index / columns) * 340,
      })
      const node = this.nodes.find((item) => item.id === id)
      node.data = {
        ...node.data,
        title: `${plan.label}分镜板`,
        storyboardSourceId: plannerId,
        storyboardTemplateId: 'ugc-seeding',
        storyboardTemplateLabel: plan.label,
        storyboardDuration: planner.data.duration,
        storyboardVideoAspectRatio: planner.data.videoAspectRatio,
        storyboardShotCount: storyboardShotCount(planner.data.duration),
        storyboardProductReferences: referenceManifest.products,
        storyboardCharacterReferences: referenceManifest.characters,
        videoPrompt: plan.videoPrompt,
        prompt: plan.prompt,
        promptParts: [{ type: 'text', value: plan.prompt }],
        ...settings,
      }
      this.addEdge({ source: plannerId, target: id })
      this.addEdge({ source: productId, target: id })
      return id
    })
    this.selectNodes(ids.slice(0, 1))
    return ids
  },

  syncProductStoryboardReferences(plannerId, productReferences = [], characterReferences = []) {
    const manifest = buildStoryboardReferenceManifest(characterReferences, productReferences)
    const references = manifest.products.map((reference) => ({ ...reference }))
    const characters = manifest.characters.map((reference) => ({ ...reference }))
    const storyboardImageIds = new Set(this.nodes
      .filter((node) => node.type === 'image' && node.data.storyboardSourceId === plannerId)
      .map((node) => node.id))
    this.nodes
      .filter((node) => ['image', 'video'].includes(node.type)
        && (node.data.storyboardSourceId === plannerId || storyboardImageIds.has(node.data.storyboardImageId)))
      .forEach((node) => {
        node.data.storyboardProductReferences = references.map((reference) => ({ ...reference }))
        node.data.storyboardCharacterReferences = characters.map((reference) => ({ ...reference }))
      })
  },

  addApparelStoryboardNodes(plannerId, garmentId, modelId, sceneId, plan, settings = {}) {
    const planner = this.nodes.find((node) => node.id === plannerId)
    if (!planner || !plan?.storyboardPrompt?.trim() || !plan.videoPrompt?.trim()) return []
    const imageSettings = settings.imageSettings || {
      model: 'gpt-image-2',
      aspectRatio: planner.data.videoAspectRatio,
      resolution: '2K',
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

  addStoryboardVideoNode(imageId) {
    const image = this.nodes.find((node) => node.id === imageId && node.type === 'image')
    if (!image?.data.asset || !image.data.videoPrompt?.trim()) return
    const existing = this.nodes.find((node) => node.type === 'video' && node.data.storyboardImageId === imageId)
    if (existing) {
      Object.assign(existing.data, storyboardVideoData(image))
      this.selectNodes([existing.id])
      return existing.id
    }
    const id = this.addNode('video', { x: image.position.x + 500, y: image.position.y }, imageId)
    const node = this.nodes.find((item) => item.id === id)
    if (!node) return
    node.data.title = `${image.data.storyboardTemplateLabel || '商品分镜'}视频`
    this.selectNodes([id])
    return id
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

  addCharacterVisualNodes(characterId, referenceId, plans, settings) {
    const character = this.nodes.find((node) => node.id === characterId)
    if (!character || !plans.length) return []
    const ids = plans.map((plan, index) => {
      const id = this.addNode('image', {
        x: character.position.x + 500 + index * 440,
        y: character.position.y,
      })
      const node = this.nodes.find((item) => item.id === id)
      node.data = {
        ...node.data,
        title: plan.label,
        characterSourceId: characterId,
        prompt: plan.prompt,
        promptParts: [{ type: 'text', value: plan.prompt }],
        ...settings,
      }
      this.addEdge({ source: characterId, target: id })
      if (referenceId) this.addEdge({ source: referenceId, target: id })
      return id
    })
    this.selectNodes(ids.slice(0, 1))
    return ids
  },
}
