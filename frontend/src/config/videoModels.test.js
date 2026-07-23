import { describe, expect, it } from 'vitest'

import { buildVideoRequest, getVideoReferenceError } from './videoModels'

const imageNode = (id) => ({ id, type: 'image', data: { asset: `https://example.com/${id}.png` } })

describe('buildVideoRequest', () => {
  it('builds a standard Seedance reference request', () => {
    expect(buildVideoRequest({
      model: 'seedance-2',
      prompt: 'test video',
      duration: 5,
      resolution: '720p',
      aspectRatio: '16:9',
      generateAudio: false,
    }, [imageNode('one')])).toEqual({
      model: 'seedance-2',
      prompt: 'test video',
      duration: 5,
      resolution: '720p',
      aspect_ratio: '16:9',
      generate_audio: false,
      reference_images: ['https://example.com/one.png'],
    })
  })

  it('omits unsupported HappyHorse parameters', () => {
    const request = buildVideoRequest({
      model: 'happyhorse-1.1',
      prompt: 'test video',
      duration: 5,
      resolution: '1080P',
      aspectRatio: '16:9',
    }, [imageNode('one')])
    expect(request.reference_images).toEqual(['https://example.com/one.png'])
    expect(request).not.toHaveProperty('generate_audio')
    expect(request).not.toHaveProperty('action')
  })

  it('rejects unsupported media references and excess images', () => {
    expect(getVideoReferenceError({}, [{ type: 'video', data: { asset: 'https://example.com/a.mp4' } }])).toContain('仅支持图片')
    expect(getVideoReferenceError({}, Array.from({ length: 10 }, (_, index) => imageNode(index)))).toContain('最多支持 9 张')
  })
})
