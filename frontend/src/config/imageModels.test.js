import { describe, expect, it } from 'vitest'
import { buildImageRequest } from './imageModels'

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
})
