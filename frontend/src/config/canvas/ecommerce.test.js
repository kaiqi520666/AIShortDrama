import { describe, expect, it } from 'vitest'
import { mergeProductProfile, parseProductProfile } from './ecommerce'

describe('product profile parsing', () => {
  it('parses fenced JSON and normalizes selling point arrays', () => {
    const product = parseProductProfile('```json\n{"name":"冲锋衣","brand":"Moon","sellingPoints":["防风","轻量"]}\n```')

    expect(product).toEqual(expect.objectContaining({
      name: '冲锋衣',
      brand: 'Moon',
      sellingPoints: '防风\n轻量',
      category: '',
    }))
  })

  it('rejects non-JSON responses', () => {
    expect(() => parseProductProfile('无法识别')).toThrow('未识别到有效的商品档案')
  })

  it('keeps manually entered fields when merging recognition results', () => {
    expect(mergeProductProfile({ name: '手填名称' }, { name: '识别名称', brand: '识别品牌' })).toEqual(expect.objectContaining({
      name: '手填名称',
      brand: '识别品牌',
    }))
  })
})
