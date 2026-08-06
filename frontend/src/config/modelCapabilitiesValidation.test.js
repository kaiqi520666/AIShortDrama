import fixture from '../../../contracts/generation-capabilities.v1.json'
import { describe, expect, it } from 'vitest'
import { validateModelCapabilities } from './modelCapabilitiesValidation'

describe('model capability response validation', () => {
  it('accepts the shared v1 contract', () => {
    expect(validateModelCapabilities(fixture)).toBe('')
  })

  it('rejects unsupported versions and missing defaults', () => {
    const unsupported = structuredClone(fixture)
    unsupported.version = 2
    const missingDefault = structuredClone(fixture)
    missingDefault.video.default_model = 'missing'

    expect(validateModelCapabilities(unsupported)).toBe('模型能力版本不兼容')
    expect(validateModelCapabilities(missingDefault)).toBe('video 默认模型不存在')
  })

  it('rejects malformed video and audio limits', () => {
    const invalidVideo = structuredClone(fixture)
    delete invalidVideo.video.models[0].duration
    const invalidAudio = structuredClone(fixture)
    invalidAudio.audio.models[0].reference_limits.audio = -1

    expect(validateModelCapabilities(invalidVideo)).toBe('视频时长配置无效')
    expect(validateModelCapabilities(invalidAudio)).toBe('音频引用限制无效')
  })
})
