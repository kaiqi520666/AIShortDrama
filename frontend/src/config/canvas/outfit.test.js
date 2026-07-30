import { describe, expect, it } from 'vitest'
import { buildOutfitPlanPrompt, outfitMaterialGroups, outfitMaterials, parseOutfitPlan, resolveOutfitMaterials } from './outfit'

describe('outfit planning', () => {
  it('provides categorized reusable material modules', () => {
    expect(outfitMaterialGroups.map((group) => group.label)).toEqual(['固定六格参考图板'])
    expect(outfitMaterials).toHaveLength(6)
    expect(outfitMaterials.map((item) => item.id)).toEqual(['front', 'three-quarter', 'back', 'turn', 'fabric', 'lifestyle'])
  })

  it('always returns the fixed six reference views', () => {
    const materials = resolveOutfitMaterials(['front', 'street'], '突出秋季氛围')
    const prompt = buildOutfitPlanPrompt(materials, '突出秋季氛围', { aspectRatio: '3:4', resolution: '2K' }, '单品1：白色衬衫')

    expect(materials).toHaveLength(6)
    expect(materials.map((item) => item.id)).toEqual(['front', 'three-quarter', 'back', 'turn', 'fabric', 'lifestyle'])
    expect(prompt).toContain('统一补充要求：突出秋季氛围')
    expect(prompt).toContain('统一画面规格：9:16，4K')
    expect(prompt).toContain('单品1：白色衬衫')
    expect(prompt).toContain('不描述说话、台词、音效、运镜或连续动作')
  })

  it('keeps the fixed views when no custom requirement is provided', () => {
    expect(resolveOutfitMaterials()).toHaveLength(6)
  })

  it('parses one prompt for every requested module', () => {
    const materials = resolveOutfitMaterials()
    const content = JSON.stringify(materials.map((item) => ({ type: item.id, prompt: `${item.label}穿搭` })))
    expect(parseOutfitPlan(content, materials)).toHaveLength(6)
    expect(parseOutfitPlan(content, materials)[0]).toEqual(expect.objectContaining({ id: 'front', prompt: '正面全身穿搭' }))
  })

})
