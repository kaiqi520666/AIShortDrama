import { describe, expect, it } from 'vitest'
import { buildWorldPrompt, parseWorldProfile, worldReady } from './drama'

describe('drama world creation', () => {
  it('builds a structured world prompt from settings and story idea', () => {
    const prompt = buildWorldPrompt({
      setting: { genre: '悬疑', era: '当代', location: '沿海小城', civilization: '现实社会', ruleSeed: '记忆可以交易', visualStyle: '电影写实', tone: '暗黑' },
      prompt: '失忆记者调查一座只在雨夜出现的旅馆',
    })

    expect(prompt).toContain('题材：悬疑')
    expect(prompt).toContain('故事想法：失忆记者')
    expect(prompt).toContain('"visualGuide"')
  })

  it('parses fenced JSON and validates every result field', () => {
    const content = '```json\n{"overview":"概述","timeSpace":"时空","society":"社会","rules":"规则","conflict":"矛盾","visualGuide":"视觉"}\n```'
    const world = parseWorldProfile(content)

    expect(worldReady(world)).toBe(true)
    expect(world.conflict).toBe('矛盾')
    expect(() => parseWorldProfile('{"overview":"只有概述"}')).toThrow('缺少必要内容')
  })
})
