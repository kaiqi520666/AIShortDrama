import { describe, expect, it } from 'vitest'
import { buildAudioRequest, getAudioReferenceError, normalizeAudioSettings } from './audioModels'

const reference = (type, id, data = {}) => ({ id, type, data: { asset: `https://example.com/${id}`, ...data } })

describe('audio generation settings', () => {
  it('normalizes defaults and builds references in connection order', () => {
    expect(normalizeAudioSettings({})).toMatchObject({ format: 'mp3', sampleRate: 48000 })
    expect(buildAudioRequest({ prompt: '@音频1 生成旁白' }, [reference('audio', 'one.mp3'), reference('audio', 'two.mp3')])).toMatchObject({
      model: 'seed-audio-1.0-multilingual',
      prompt: '@音频1 生成旁白',
      format: 'mp3',
      sample_rate: 48000,
      reference_audios: ['https://example.com/one.mp3', 'https://example.com/two.mp3'],
    })
  })

  it('validates reference combinations and metadata', () => {
    expect(getAudioReferenceError([reference('image', 'one.png'), reference('audio', 'one.mp3')])).toContain('不能混用')
    expect(getAudioReferenceError(Array.from({ length: 4 }, (_, index) => reference('audio', `${index}.mp3`)))).toContain('最多支持 3 条')
    expect(getAudioReferenceError([reference('audio', 'long.mp3', { sourceDuration: 31 })])).toContain('30 秒')
  })
})
