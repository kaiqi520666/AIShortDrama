import { describe, expect, it } from 'vitest'
import { modelCapabilitiesFixture } from '../test/modelCapabilities'
import { buildImageRequest as buildRequest, normalizeImageModels } from './imageModels'

const imageModels = normalizeImageModels(modelCapabilitiesFixture.image)
const defaultImageModel = imageModels.find(({ id }) => id === modelCapabilitiesFixture.image.default_model)
const buildImageRequest = (data, references) => buildRequest(data, references, imageModels, defaultImageModel)

describe('buildImageRequest', () => {
  it('builds the unified image request for every model', () => {
    const request = buildImageRequest({
      model: 'gemini-3.1-flash-image-preview',
      prompt: 'test',
      aspectRatio: '1:1',
      resolution: '1K',
      googleSearch: true,
      googleImageSearch: true,
    }, ['https://example.com/garment.png', { data: { asset: 'https://example.com/model.png' } }])

    expect(request).toEqual({
      model: 'gemini-3.1-flash-image-preview',
      prompt: 'test',
      size: '1:1',
      n: 1,
      resolution: '1K',
      reference_images: ['https://example.com/garment.png', 'https://example.com/model.png'],
      google_search: true,
      google_image_search: true,
    })
  })

  it('limits GPT Image 2 to six reference images', () => {
    const references = Array.from({ length: 7 }, (_, index) => `https://example.com/reference-${index}.png`)
    expect(() => buildImageRequest({
      model: 'gpt-image-2',
      prompt: 'test',
      aspectRatio: '1:1',
      resolution: '1K',
    }, references)).toThrow('参考图片不能超过 6 张')
  })
})
