import { describe, expect, it } from 'vitest'

import { modelCapabilitiesFixture } from '../test/modelCapabilities'
import { buildVideoRequest as buildRequest, getVideoReferenceError as getReferenceError, normalizeVideoModels, normalizeVideoSettings as normalizeSettings } from './videoModels'

const videoModels = normalizeVideoModels(modelCapabilitiesFixture.video)
const defaultVideoModel = videoModels.find(({ id }) => id === modelCapabilitiesFixture.video.default_model)
const videoAspectRatios = defaultVideoModel.aspectRatios
const normalizeVideoSettings = (data) => normalizeSettings(data, videoModels, defaultVideoModel)
const buildVideoRequest = (data, references) => buildRequest(data, references, videoModels, defaultVideoModel)
const getVideoReferenceError = (data, references) => getReferenceError(data, references, videoModels, defaultVideoModel)

const imageNode = (id) => ({ id, type: 'image', data: { asset: `https://example.com/${id}.png` } })
const mediaNode = (type, id) => ({ id, type, data: { asset: `https://example.com/${id}.${type === 'audio' ? 'mp3' : 'mp4'}` } })

describe('buildVideoRequest', () => {
  it('uses Seedance 2 Mini as the default video model', () => {
    expect(defaultVideoModel.id).toBe('seedance-2-mini')
    expect(normalizeVideoSettings({}).model.id).toBe('seedance-2-mini')
  })

  it('replaces legacy automatic duration with the fixed default', () => {
    expect(normalizeVideoSettings({ model: 'seedance-2', duration: 0 }).duration).toBe(5)
    expect(normalizeVideoSettings({ model: 'seedance-2-fast', duration: 0 }).duration).toBe(5)
  })

  it('keeps synchronized audio enabled by default', () => {
    expect(normalizeVideoSettings({ model: 'seedance-2' }).generateAudio).toBe(true)
    expect(normalizeVideoSettings({ model: 'seedance-2', generateAudio: false }).generateAudio).toBe(false)
  })

  it('uses six fixed video ratios without adaptive billing', () => {
    expect(videoAspectRatios).toEqual(['21:9', '16:9', '4:3', '1:1', '3:4', '9:16'])
    expect(videoModels.filter((model) => model.id.startsWith('seedance')).every((model) => !model.aspectRatios.includes('adaptive'))).toBe(true)
    expect(normalizeVideoSettings({ model: 'seedance-2', aspectRatio: 'adaptive' }).aspectRatio).toBe('16:9')
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
      return_last_frame: true,
      reference_images: ['https://example.com/one.png'],
      reference_videos: ['https://example.com/two.mp4'],
      reference_audios: ['https://example.com/three.mp3'],
    })
  })

  it('uses a registered avatar asset while retaining its preview image', () => {
    const avatar = { id: 'avatar', type: 'image', data: { asset: 'https://example.com/avatar.png', providerAsset: 'asset://pa_test' } }
    expect(buildVideoRequest({ model: 'seedance-2', prompt: 'test', duration: 5, resolution: '720p', aspectRatio: '16:9' }, [avatar]).reference_images).toEqual(['asset://pa_test'])
  })

  it('waits for a registered image asset to become active', () => {
    const avatar = {
      id: 'avatar',
      type: 'image',
      data: {
        asset: 'https://example.com/avatar.png',
        storyboardAsset: { status: 'processing', asset_url: 'asset://pa_test' },
      },
    }
    expect(getVideoReferenceError({ model: 'seedance-2' }, [avatar])).toContain('刷新状态')
  })

  it('uses the registered storyboard asset for Seedance', () => {
    const storyboard = {
      id: 'storyboard',
      type: 'image',
      data: {
        asset: 'https://example.com/storyboard.png',
        providerAsset: 'asset://pa_storyboard',
        storyboardSourceId: 'planner',
      },
    }
    const settings = { prompt: 'test', duration: 5, aspectRatio: '16:9' }
    expect(buildVideoRequest({ ...settings, model: 'seedance-2', resolution: '720p' }, [storyboard]).reference_images).toEqual(['asset://pa_storyboard'])
  })

  it('requests the last frame for storyboard segments', () => {
    expect(buildVideoRequest({ model: 'seedance-2', prompt: 'test', duration: 15, resolution: '720p', aspectRatio: '9:16', returnLastFrame: true }, [])).toEqual(expect.objectContaining({ return_last_frame: true }))
  })

  it('requires registration for a Seedance storyboard with a selected character', () => {
    const storyboard = {
      id: 'storyboard',
      type: 'image',
      data: {
        asset: 'https://example.com/storyboard.png',
        storyboardSourceId: 'planner',
        storyboardCharacterReferences: [{ assetUrl: 'asset://pa_character' }],
      },
    }
    expect(getVideoReferenceError({ model: 'seedance-2' }, [storyboard])).toContain('注册 Seedance 人物素材')
  })

  it('requires registration for an apparel storyboard with a model reference', () => {
    const storyboard = {
      id: 'apparel-storyboard',
      type: 'image',
      data: {
        asset: 'https://example.com/apparel-storyboard.png',
        storyboardSourceId: 'planner',
        storyboardRequiresRegistration: true,
      },
    }
    expect(getVideoReferenceError({ model: 'seedance-2' }, [storyboard])).toContain('注册 Seedance 人物素材')
  })

  it('requires registration for legacy apparel storyboard nodes', () => {
    const storyboard = {
      id: 'legacy-apparel-storyboard',
      type: 'image',
      data: {
        asset: 'https://example.com/legacy-apparel-storyboard.png',
        storyboardSourceId: 'planner',
        storyboardOutfitBoard: { url: 'https://example.com/outfit-board.jpg' },
      },
    }
    expect(getVideoReferenceError({ model: 'seedance-2' }, [storyboard])).toContain('注册 Seedance 人物素材')
  })

  it('does not recheck avatar registration on a prior storyboard video reference', () => {
    const previousVideo = {
      id: 'previous-video',
      type: 'video',
      data: {
        asset: 'https://example.com/previous.mp4',
        storyboardSourceId: 'planner',
        storyboardCharacterReferences: [{ assetUrl: 'asset://pa_character' }],
      },
    }
    expect(getVideoReferenceError({ model: 'seedance-2' }, [previousVideo])).toBe('')
  })

  it('validates model-specific reference capabilities', () => {
    expect(getVideoReferenceError({}, [mediaNode('audio', 'one')])).toContain('需同时连接图片或视频')
    expect(getVideoReferenceError({}, Array.from({ length: 10 }, (_, index) => imageNode(index)))).toContain('最多支持 9 张')
    expect(getVideoReferenceError({}, [imageNode('image'), ...Array.from({ length: 4 }, (_, index) => mediaNode('audio', index))])).toContain('最多支持 3 条参考音频')
  })
})
