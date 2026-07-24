import { describe, expect, it } from 'vitest'

import { buildVideoRequest, getVideoModelError, getVideoReferenceError, normalizeVideoSettings } from './videoModels'

const imageNode = (id) => ({ id, type: 'image', data: { asset: `https://example.com/${id}.png` } })
const mediaNode = (type, id) => ({ id, type, data: { asset: `https://example.com/${id}.${type === 'audio' ? 'mp3' : 'mp4'}` } })

describe('buildVideoRequest', () => {
  it('replaces legacy automatic duration with the fixed default', () => {
    expect(normalizeVideoSettings({ model: 'seedance-2', duration: 0 }).duration).toBe(5)
    expect(normalizeVideoSettings({ model: 'seedance-2-fast', duration: 0 }).duration).toBe(5)
  })

  it('builds a standard Seedance reference request', () => {
    expect(buildVideoRequest({
      model: 'seedance-2',
      prompt: 'test video',
      duration: 5,
      resolution: '720p',
      aspectRatio: '16:9',
      generateAudio: false,
    }, [imageNode('one'), mediaNode('video', 'two'), mediaNode('audio', 'three')])).toEqual({
      model: 'seedance-2',
      prompt: 'test video',
      duration: 5,
      resolution: '720p',
      aspect_ratio: '16:9',
      generate_audio: false,
      reference_images: ['https://example.com/one.png'],
      reference_videos: ['https://example.com/two.mp4'],
      reference_audios: ['https://example.com/three.mp3'],
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

  it('validates model-specific reference capabilities', () => {
    expect(getVideoModelError({ model: 'happyhorse-1.1' }, [mediaNode('audio', 'one')])).toContain('不支持参考音频')
    expect(getVideoModelError({ model: 'happyhorse-1.1' }, [mediaNode('video', 'one')])).toContain('不支持参考视频')
    expect(getVideoReferenceError({}, [mediaNode('audio', 'one')])).toContain('需同时连接图片或视频')
    expect(getVideoReferenceError({}, Array.from({ length: 10 }, (_, index) => imageNode(index)))).toContain('最多支持 9 张')
    expect(getVideoReferenceError({}, [imageNode('image'), ...Array.from({ length: 4 }, (_, index) => mediaNode('audio', index))])).toContain('最多支持 3 条参考音频')
  })
})
