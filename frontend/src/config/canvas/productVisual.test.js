import { describe, expect, it } from 'vitest'
import { buildProductVisualPrompt, parseProductVisualPlan, productVisualTypes } from './productVisual'

describe('product visual planning', () => {
  it('builds one bounded multimodal prompt for all selected types', () => {
    const prompt = buildProductVisualPrompt('商品名称：测试商品\n核心卖点：轻便耐用'.repeat(200), productVisualTypes, { aspectRatio: '16:9', resolution: '2K' })

    expect(prompt.length).toBeLessThanOrEqual(3000)
    expect(prompt).toContain('white-bg=白底图')
    expect(prompt).toContain('usage-tips=使用建议')
    expect(prompt).toContain('16:9，2K')
  })

  it('parses and orders generated prompts by the selected types', () => {
    const items = productVisualTypes.slice(0, 2)
    const plans = parseProductVisualPlan('```json\n[{"type":"first-screen","prompt":"主视觉"},{"type":"white-bg","prompt":"白底"}]\n```', items)

    expect(plans).toEqual([
      expect.objectContaining({ id: 'white-bg', prompt: '白底' }),
      expect.objectContaining({ id: 'first-screen', prompt: '主视觉' }),
    ])
  })

  it('rejects incomplete generated plans', () => {
    expect(() => parseProductVisualPlan('[{"type":"white-bg","prompt":"白底"}]', productVisualTypes.slice(0, 2))).toThrow('缺少')
  })
})
