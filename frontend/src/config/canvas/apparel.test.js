import { describe, expect, it } from 'vitest'
import { apparelPromptContext, parseApparelProfile } from './apparel'

describe('apparel profile', () => {
  it('parses a multi-item outfit into an editable array', () => {
    const profile = parseApparelProfile('```json\n{"compositionType":"set","summary":"黑白商务套装","items":[{"name":"白色衬衫","category":"衬衫","color":"白色"},{"name":"黑色皮鞋","category":"鞋履","material":"皮革"}]}\n```')

    expect(profile.compositionType).toBe('set')
    expect(profile.items).toEqual([
      expect.objectContaining({ id: 'item-1', name: '白色衬衫', category: '衬衫', enabled: true }),
      expect.objectContaining({ id: 'item-2', name: '黑色皮鞋', category: '鞋履', enabled: true }),
    ])
  })

  it('derives a single-item profile and rejects empty results', () => {
    expect(parseApparelProfile('{"compositionType":"single","items":[{"name":"直筒西裤","category":"裤装"}]}').compositionType).toBe('single')
    expect(() => parseApparelProfile('{"items":[]}')).toThrow('未识别到服饰单品')
  })

  it('builds context from enabled items only', () => {
    const context = apparelPromptContext({
      compositionType: 'set',
      summary: '度假穿搭',
      items: [
        { enabled: true, name: '短袖上衣', category: '上衣', color: '米白色', material: '棉麻', silhouette: '短款', details: '一字领' },
        { enabled: false, name: '凉鞋', category: '鞋履' },
      ],
    })
    expect(context).toContain('服饰类型：整套搭配')
    expect(context).toContain('单品1：短袖上衣')
    expect(context).not.toContain('凉鞋')
  })
})
