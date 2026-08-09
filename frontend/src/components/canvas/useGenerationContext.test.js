import { beforeEach, describe, expect, it, vi } from 'vitest'
import { reactive, ref } from 'vue'
import { createAudioGeneration, createImageGeneration, createVideoGeneration } from '../../api/generations'
import { useGenerationContext } from './useGenerationContext'

vi.mock('../../api/generations', () => ({
  createAudioGeneration: vi.fn(),
  createImageGeneration: vi.fn(),
  createVideoGeneration: vi.fn(),
}))
vi.mock('../../api/reversals', () => ({ streamReversePrompt: vi.fn() }))

const imageModel = {
  id: 'image-1', label: '图片模型', resolutions: ['1K'], aspectRatios: ['1:1'],
  defaultResolution: '1K', defaultAspectRatio: '1:1', maxPromptLength: 100, maxReferences: 2,
  search: false, imageSearch: false,
}
const videoModel = {
  id: 'video-1', label: '视频模型', resolutions: ['720p'], aspectRatios: ['16:9'],
  defaultResolution: '720p', defaultAspectRatio: '16:9', defaultDuration: 5, durationMin: 3,
  durationMax: 10, durationOptions: [5, 10], maxPromptLength: 100, generateAudio: true,
  returnLastFrame: false, requiresPrivateAsset: true, referenceLimits: { image: 1, video: 1, audio: 1 },
}
const audioCapability = {
  model: { id: 'audio-1', label: '音频模型' },
  formatOptions: [{ value: 'mp3', label: 'MP3' }],
  sampleRateOptions: [{ value: 48000, label: '48 kHz' }],
  defaults: { model: 'audio-1', format: 'mp3', sampleRate: 48000, speechRate: 0, loudnessRate: 0, pitchRate: 0 },
  parameters: {
    speech_rate: { min: -50, max: 100, default: 0 },
    loudness_rate: { min: -50, max: 100, default: 0 },
    pitch_rate: { min: -12, max: 12, default: 0 },
  },
  referenceLimits: { image: 1, audio: 3 },
  referenceAudioMaxSeconds: 30,
  referenceMaxBytes: 20 * 1024 * 1024,
  maxPromptLength: 100,
}
const textModel = { id: 'text-1', label: '文本模型', maxPromptLength: 100 }

function createSubject(type, data, incomingNodes = []) {
  const props = reactive({ nodeId: `${type}-1`, type, data: reactive(data) })
  const updateNodeData = vi.fn((_, updates) => Object.assign(props.data, updates))
  const authStore = {
    user: { credit_balance: 100 },
    estimateCredits: vi.fn(() => 3),
    refreshCredits: vi.fn().mockResolvedValue(),
  }
  const store = {
    workspaceId: 'workspace-1',
    incomingNodes: vi.fn(() => incomingNodes),
    invalidateStoryboardFrom: vi.fn(),
    setStoryboardContinuityMode: vi.fn(),
    confirmStoryboardSegment: vi.fn(() => true),
  }
  const capabilityStore = {
    imageModels: [imageModel],
    defaultImageModel: imageModel,
    videoModels: [videoModel],
    defaultVideoModel: videoModel,
    textModels: [textModel],
    defaultTextModel: textModel,
    audioCapability,
  }
  const runTextTask = vi.fn(async (_streamer, _payload, options) => options.onSuccess?.('{"name":"测试商品"}'))
  const context = useGenerationContext({
    props,
    store,
    authStore,
    capabilityStore,
    updateNodeData,
    confirm: vi.fn(async () => true),
    toast: { warning: vi.fn() },
    runTextTask,
    failure: ref(''),
  })
  return { context, props, store, authStore, updateNodeData, runTextTask }
}

beforeEach(() => {
  vi.clearAllMocks()
  for (const submitter of [createImageGeneration, createVideoGeneration, createAudioGeneration]) {
    submitter.mockResolvedValue({ code: 0, data: { id: 'task-1', status: 'queued' } })
  }
})

describe('useGenerationContext', () => {
  it.each([
    ['image', { model: 'image-1', prompt: '生成商品主图', resolution: '1K', aspectRatio: '1:1' }, createImageGeneration],
    ['video', { model: 'video-1', prompt: '展示商品动作', duration: 5, resolution: '720p', aspectRatio: '16:9' }, createVideoGeneration],
    ['audio', { model: 'audio-1', prompt: '生成旁白', format: 'mp3', sampleRate: 48000 }, createAudioGeneration],
  ])('submits %s through its adapter and refreshes credits', async (type, data, submitter) => {
    const { context, updateNodeData, authStore } = createSubject(type, data)

    expect(context.canSubmit.value).toBe(true)
    await context.submitTask()

    expect(submitter).toHaveBeenCalledWith(expect.objectContaining({ workspace_id: 'workspace-1', node_id: `${type}-1` }))
    expect(updateNodeData).toHaveBeenCalledWith(`${type}-1`, expect.objectContaining({ generationTaskId: 'task-1' }))
    expect(authStore.refreshCredits).toHaveBeenCalledOnce()
  })

  it('dispatches product recognition as a text operation', async () => {
    const reference = { id: 'image-1', type: 'image', data: { asset: 'https://cdn.test/product.png' } }
    const { context, runTextTask, updateNodeData } = createSubject(
      'product',
      { model: 'text-1', prompt: '', product: {} },
      [reference],
    )

    await context.submitTask()

    expect(runTextTask).toHaveBeenCalledWith(expect.any(Function), expect.objectContaining({
      response_mode: 'product_profile',
      media_url: 'https://cdn.test/product.png',
    }), expect.objectContaining({ failureMessage: '商品识别失败', preservePartial: false }))
    expect(updateNodeData).not.toHaveBeenCalledWith('product-1', expect.objectContaining({ status: 'generating' }))
  })

  it('updates prompt parts into stable node references', () => {
    const reference = { id: 'image-1', type: 'image', data: { asset: 'https://cdn.test/a.png' } }
    const { context, updateNodeData } = createSubject('video', { model: 'video-1', prompt: '' }, [reference])

    context.updatePrompt([
      { type: 'text', value: '展示' },
      { type: 'image', nodeId: 'image-1' },
    ])

    expect(updateNodeData).toHaveBeenCalledWith('video-1', {
      promptParts: [
        { type: 'text', value: '展示' },
        { type: 'image', nodeId: 'image-1' },
      ],
      prompt: '展示@图片1',
    })
  })

  it('uses the registered person asset from an ordinary image node', async () => {
    const reference = {
      id: 'image-1',
      type: 'image',
      data: {
        asset: 'https://cdn.test/person.png',
        storyboardAsset: { status: 'active', asset_url: 'asset://person-1' },
      },
    }
    const { context } = createSubject('video', {
      model: 'video-1',
      prompt: '人物展示服装',
      duration: 5,
      resolution: '720p',
      aspectRatio: '16:9',
    }, [reference])

    await context.submitTask()

    expect(createVideoGeneration).toHaveBeenCalledWith(expect.objectContaining({
      reference_images: ['asset://person-1'],
    }))
  })
})
