import { describe, expect, it } from 'vitest'
import { contentTemplatesFixture } from '../../test/contentTemplates'
import { validateProductContentTemplates } from './contentTemplates'

describe('product content template contract', () => {
  it('accepts the public UGC and commerce drama templates', () => {
    expect(validateProductContentTemplates(structuredClone(contentTemplatesFixture))).toBe('')
  })

  it('rejects a missing or incompatible commerce drama template', () => {
    const missing = structuredClone(contentTemplatesFixture)
    delete missing.commerce_drama
    expect(validateProductContentTemplates(missing)).toBe('商品模板响应无效')

    const invalid = structuredClone(contentTemplatesFixture)
    invalid.commerce_drama.config.output_protocol_id = 'changed'
    expect(validateProductContentTemplates(invalid)).toBe('短剧带货输出协议无效')
  })
})
