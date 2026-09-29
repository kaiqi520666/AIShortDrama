import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { i18n } from '../../i18n'

import { buildProductVisualRequest, createProductVisualItems, parseProductVisualPlan } from './productVisual'
import { contentTemplatesFixture } from '../../test/contentTemplates'

beforeEach(() => { i18n.global.locale.value = 'zh-CN' })
afterEach(() => { i18n.global.locale.value = 'id' })

const template = contentTemplatesFixture.product_visual
const productVisualTypes = createProductVisualItems(template)

describe('product visual planning', () => {
  it('derives selectable items from the public template', () => {
    expect(productVisualTypes[0]).toEqual({ id: 'white-bg', label: '白底图', enabled: true })
    expect(productVisualTypes.at(-1)).toEqual({ id: 'usage-tips', label: '使用建议', enabled: false })
  })

  it('builds a structured server-template request without a prompt', () => {
    const request = buildProductVisualRequest({
      workspaceId: 'workspace-1',
      nodeId: 'visual-1',
      model: 'gpt-5.6-sol',
      referenceUrls: ['https://example.com/1.png', 'https://example.com/2.png'],
      productContext: '商品名称：测试商品',
      selectedTypeIds: ['white-bg', 'core-selling'],
      aspectRatio: '16:9',
      resolution: '2K',
      templateVersion: 3,
    })

    expect(request).not.toHaveProperty('prompt')
    expect(request.template_key).toBe('product_visual')
    expect(request.template_context).toEqual({
      product_context: '商品名称：测试商品',
      selected_type_ids: ['white-bg', 'core-selling'],
      aspect_ratio: '16:9',
      resolution: '2K',
      reference_count: 2,
    })
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
