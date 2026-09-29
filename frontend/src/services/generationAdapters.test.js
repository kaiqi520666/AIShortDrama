import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { i18n } from '../i18n'

import { createImageGeneration } from '../api/generations'
import { generationAdapters, getGenerationAdapter } from './generationAdapters'

beforeEach(() => { i18n.global.locale.value = 'zh-CN' })
afterEach(() => { i18n.global.locale.value = 'id' })

vi.mock('../api/generations', () => ({
  createAudioGeneration: vi.fn(async (payload) => ({ code: 0, data: payload })),
  createImageGeneration: vi.fn(async (payload) => ({ code: 0, data: payload })),
  createVideoGeneration: vi.fn(async (payload) => ({ code: 0, data: payload })),
}))

vi.mock('../api/reversals', () => ({ streamReversePrompt: vi.fn() }))

beforeEach(() => vi.clearAllMocks())

describe('generation adapters', () => {
  it('exposes a consistent interface for every media type', () => {
    Object.values(generationAdapters).forEach((adapter) => {
      expect(adapter).toEqual(expect.objectContaining({
        normalize: expect.any(Function),
        validate: expect.any(Function),
        buildRequest: expect.any(Function),
        submit: expect.any(Function),
      }))
    })
    expect(() => getGenerationAdapter('missing')).toThrow('未注册适配器')
  })

  it('builds and submits a queued image request', async () => {
    const model = {
      id: 'image-model',
      resolutions: ['1K'],
      aspectRatios: ['1:1'],
      defaultResolution: '1K',
      defaultAspectRatio: '1:1',
      maxPromptLength: 100,
      maxReferences: 2,
    }
    const adapter = getGenerationAdapter('image')
    const context = {
      workspaceId: 'workspace-1',
      nodeId: 'image-1',
      data: { model: model.id, resolution: '1K', aspectRatio: '1:1' },
      prompt: '商品主图',
      imageReferences: [{ data: { asset: 'https://example.com/product.png' } }],
      imageModels: [model],
      defaultImageModel: model,
    }

    const payload = adapter.buildRequest(context)
    await adapter.submit(payload)

    expect(payload).toMatchObject({ workspace_id: 'workspace-1', node_id: 'image-1', prompt: '商品主图' })
    expect(createImageGeneration).toHaveBeenCalledWith(payload)
  })

  it('dispatches product recognition through the text operation', async () => {
    const runTextTask = vi.fn(async (_streamer, _payload, options) => options.onSuccess('{"name":"测试商品"}'))
    const adapter = getGenerationAdapter('text')
    const context = {
      workspaceId: 'workspace-1',
      nodeId: 'product-1',
      data: { product: { name: '' } },
      prompt: '',
      operation: 'productRecognition',
      mediaType: 'image',
      imageReferences: [{ data: { asset: 'https://example.com/product.png' } }],
      textModel: { id: 'text-model' },
      runTextTask,
    }

    const result = await adapter.submit(adapter.buildRequest(context), context)

    expect(runTextTask.mock.calls[0][1]).toMatchObject({ response_mode: 'product_profile', media_type: 'image' })
    expect(result).toMatchObject({ workflowStep: 'visual', product: { name: '测试商品' } })
  })
})
