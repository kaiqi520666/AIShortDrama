import { describe, expect, it } from 'vitest'

import { getEffectivePrompt } from './generationPrompt'

describe('getEffectivePrompt', () => {
  it('merges upstream text and ignores non-text media metadata', () => {
    const prompt = getEffectivePrompt({ prompt: '让 @图片1 跟随 @视频1 的运镜，并参考 @音频1' }, [
      { type: 'text', data: { content: '保持产品主体清晰' } },
      { type: 'image', data: { asset: 'image.png' } },
    ])

    expect(prompt).toBe('保持产品主体清晰\n让 @图片1 跟随 @视频1 的运镜，并参考 @音频1')
  })
})
