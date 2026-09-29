import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { i18n } from '../../i18n'

import { mergeProductProfile, parseProductProfile, productPromptContext } from './ecommerce'

beforeEach(() => { i18n.global.locale.value = 'zh-CN' })
afterEach(() => { i18n.global.locale.value = 'id' })

describe('product profile parsing', () => {
  it('parses fenced JSON and normalizes selling point arrays', () => {
    const product = parseProductProfile('```json\n{"name":"冲锋衣","brand":"Moon","sellingPoints":["防风","轻量"],"additionalInfo":"可机洗"}\n```')

    expect(product).toEqual(expect.objectContaining({
      name: '冲锋衣',
      brand: 'Moon',
      sellingPoints: '防风\n轻量',
      additionalInfo: '可机洗',
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

  it('adds product and packaging scale data to generation context', () => {
    const context = productPromptContext({
      name: '鲜炖花胶',
      packagingType: '带包装',
      productDimensions: '单瓶高8.5cm，直径6cm',
      packageDimensions: '礼盒28×20×8cm',
      packageRelation: '6瓶/盒，单瓶竖直排列',
      scaleReference: '成人单手可握，瓶身约为掌长80%',
    })
    expect(context).toContain('商品形态：带包装')
    expect(context).toContain('主体尺寸：单瓶高8.5cm，直径6cm')
    expect(context).toContain('外包装尺寸：礼盒28×20×8cm')
    expect(context).toContain('包装关系：6瓶/盒，单瓶竖直排列')
    expect(context).toContain('尺度参照：成人单手可握，瓶身约为掌长80%')
  })

  it('omits stale package fields for unpackaged products', () => {
    const context = productPromptContext({ packagingType: '无包装', productDimensions: '长12cm', packageDimensions: '旧包装尺寸' })
    expect(context).toContain('主体尺寸：长12cm')
    expect(context).not.toContain('旧包装尺寸')
  })
})
