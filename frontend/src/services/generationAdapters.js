import { createAudioGeneration, createImageGeneration, createVideoGeneration } from '../api/generations'
import { streamReversePrompt } from '../api/reversals'
import { buildAudioRequest, normalizeAudioSettings } from '../config/audioModels'
import { mergeProductProfile, parseProductProfile } from '../config/canvas/ecommerce'
import { maxProductReferenceImages } from '../config/canvas/connectionRules'
import { buildImageRequest, normalizeImageSettings } from '../config/imageModels'
import { buildVideoRequest, normalizeVideoSettings } from '../config/videoModels'

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
    if (!primaryReference?.data.asset) throw new Error('请先上传参考图片')
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
      failureMessage: productRecognition ? '商品识别失败' : '反推生成失败',
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
  if (!adapter) throw new Error(`生成类型 ${type} 未注册适配器`)
  return adapter
}
