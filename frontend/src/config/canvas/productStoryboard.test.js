import { describe, expect, it } from 'vitest'
import {
  buildProductStoryboardPrompt,
  parseProductStoryboardPlan,
  recommendStoryboardSettings,
  storyboardGrid,
  storyboardShotCount,
  storyboardTemplates,
} from './productStoryboard'

describe('product storyboard planning', () => {
  it('maps 4 to 15 seconds to the expected shot counts', () => {
    expect([4, 6, 9, 12, 15].map(storyboardShotCount)).toEqual([2, 3, 4, 6, 6])
    expect(storyboardGrid(15, '9:16')).toEqual({ shots: 6, columns: 3, rows: 2 })
    expect(storyboardGrid(15, '16:9')).toEqual({ shots: 6, columns: 2, rows: 3 })
  })

  it('recommends editable image settings from duration and video ratio', () => {
    expect(recommendStoryboardSettings(9, '9:16')).toEqual(expect.objectContaining({ shots: 4, aspectRatio: '9:16', resolution: '2K' }))
    expect(recommendStoryboardSettings(15, '9:16')).toEqual(expect.objectContaining({ shots: 6, aspectRatio: '4:5', resolution: '4K' }))
  })

  it('builds one bounded prompt for every selected template', () => {
    const prompt = buildProductStoryboardPrompt('商品名称：测试商品\n核心卖点：轻便耐用'.repeat(200), storyboardTemplates, {
      duration: 8,
      videoAspectRatio: '9:16',
      prompt: '节奏轻快',
    })
    expect(prompt.length).toBeLessThanOrEqual(3000)
    expect(prompt).toContain('ugc-seeding=UGC 种草')
    expect(prompt).toContain('reaction=反应展示')
    expect(prompt).toContain('3 个镜头')
    expect(prompt).toContain('3 列 × 1 行')
    expect(prompt).toContain('videoPrompt')
    expect(prompt).toContain('不超过 500 个中文字符')
  })

  it('orders parsed prompts by selected template order', () => {
    const plans = parseProductStoryboardPlan('[{"type":"sales-drama","prompt":"短剧分镜","videoPrompt":"短剧视频"},{"type":"ugc-seeding","prompt":"种草分镜","videoPrompt":"种草视频"}]', storyboardTemplates.slice(0, 2))
    expect(plans.map((item) => item.prompt)).toEqual(['种草分镜', '短剧分镜'])
    expect(plans.map((item) => item.videoPrompt)).toEqual(['种草视频', '短剧视频'])
  })

  it('rejects incomplete template plans', () => {
    expect(() => parseProductStoryboardPlan('[{"type":"ugc-seeding","prompt":"种草分镜"}]', storyboardTemplates.slice(0, 2))).toThrow('缺少')
  })
})
