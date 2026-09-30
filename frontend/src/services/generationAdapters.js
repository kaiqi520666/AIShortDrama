import { i18n } from '../i18n/index'
import { createAudioGeneration, createImageGeneration, createVideoGeneration } from '../api/generations'
import { streamReversePrompt } from '../api/reversals'
import { buildAudioRequest, normalizeAudioSettings } from '../config/audioModels'
import { mergeProductProfile, parseProductProfile } from '../config/canvas/ecommerce'
import { maxProductReferenceImages } from '../config/canvas/connectionRules'
import { buildImageRequest, normalizeImageSettings } from '../config/imageModels'
import { buildVideoRequest, normalizeVideoSettings } from '../config/videoModels'

const { t } = i18n.global

export const TERMINAL_GENERATION_STATUSES = new Set(['succeeded', 'failed', 'cancelled', 'timeout'])
export const MEDIA_LABEL_KEYS = { image: 'canvas.image', video: 'canvas.video', audio: 'canvas.audio' }

export function isTerminalGenerationStatus(status) {
  return TERMINAL_GENERATION_STATUSES.has(status)
}

export function normalizeGenerationResult(task) {
  if (task?.result?.type === 'text') {
    return { type: 'text', content: task.result.content || '' }
  }
  const generated = task?.result?.data?.[0]
  return {
    type: task?.task_type || task?.result?.type,
    asset: generated?.url || '',
    assetId: generated?.asset_id || '',
    duration: generated?.duration,
    lastFrameUrl: task?.result?.last_frame_url || '',
  }
}

export function generationSuccessNodeData(task) {
  const result = normalizeGenerationResult(task)
  if (result.type === 'text') {
    return {
      content: result.content,
      status: 'ready',
      generationProgress: 100,
      generationError: '',
    }
  }
  return {
    ...(result.asset ? { asset: result.asset } : {}),
    ...(result.assetId ? { assetId: result.assetId } : {}),
    status: 'ready',
    generationProgress: 100,
    generationError: '',
    ...(result.duration ? { sourceDuration: result.duration } : {}),
    ...(result.type === 'video' && result.lastFrameUrl ? { lastFrameUrl: result.lastFrameUrl } : {}),
  }
}

function baseRequest(context, request) {
  return { workspace_id: context.workspaceId, node_id: context.nodeId, ...request }
}

function validate(context) {
  return context.validationError || ''
}

const imageAdapter = {
  kind: 'queued',
  normalize: ({ data, imageModels, defaultImageModel }) => normalizeImageSettings(data, imageModels, defaultImageModel),
  validate,
  buildRequest: (context) => baseRequest(context, buildImageRequest(
    { ...context.data, prompt: context.prompt },
    context.imageReferences,
    context.imageModels,
    context.defaultImageModel,
  )),
  submit: (payload) => createImageGeneration(payload),
}

const videoAdapter = {
  kind: 'queued',
  normalize: ({ data, videoModels, defaultVideoModel }) => normalizeVideoSettings(data, videoModels, defaultVideoModel),
  validate,
  buildRequest: (context) => baseRequest(context, buildVideoRequest(
    { ...context.data, prompt: context.prompt },
    context.activeReferences,
    context.videoModels,
    context.defaultVideoModel,
  )),
  submit: (payload) => createVideoGeneration(payload),
}

const audioAdapter = {
  kind: 'queued',
  normalize: ({ data, audioCapability }) => normalizeAudioSettings(data, audioCapability),
  validate,
  buildRequest: (context) => baseRequest(context, buildAudioRequest(
    { ...context.data, prompt: context.prompt },
    context.references,
    context.audioCapability,
  )),
  submit: (payload) => createAudioGeneration(payload),
}

const textAdapter = {
  kind: 'stream',
  normalize: ({ data, textModels, defaultTextModel }) => textModels.find((model) => model.id === data.model) || defaultTextModel,
  validate,
  buildRequest(context) {
    const productReferences = context.operation === 'productRecognition'
      ? context.imageReferences.slice(0, maxProductReferenceImages)
      : []
    const primaryReference = productReferences[0] || context.primaryReference
    if (!primaryReference?.data.asset) throw new Error(t('canvas.uploadReferenceFirst'))
    return baseRequest(context, {
      model: context.textModel.id,
      media_type: context.mediaType,
      media_url: primaryReference.data.asset,
      prompt: context.prompt,
      ...(productReferences.length > 1
        ? { media_urls: productReferences.slice(1).map((reference) => reference.data.asset) }
        : {}),
      ...(context.operation === 'productRecognition' ? { response_mode: 'product_profile' } : {}),
    })
  },
  submit(payload, context) {
    const productRecognition = context.operation === 'productRecognition'
    return context.runTextTask(streamReversePrompt, payload, {
      failureMessage: productRecognition ? t('canvas.productRecognitionFailed') : t('canvas.reverseFailed'),
      preservePartial: !productRecognition,
      onSuccess: (content) => productRecognition
        ? { product: mergeProductProfile(context.data.product, parseProductProfile(content)), workflowStep: 'visual' }
        : { content },
    })
  },
}

export const generationAdapters = {
  audio: audioAdapter,
  image: imageAdapter,
  text: textAdapter,
  video: videoAdapter,
}

export function getGenerationAdapter(type) {
  const adapter = generationAdapters[type]
  if (!adapter) throw new Error(t('canvas.adapterMissing', { p0: type }))
  return adapter
}
