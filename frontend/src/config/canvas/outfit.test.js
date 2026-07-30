import { describe, expect, it } from 'vitest'
import { buildOutfitPlanPrompt, outfitMaterialGroups, outfitMaterials, parseOutfitPlan, resolveOutfitMaterials } from './outfit'

describe('outfit planning', () => {
  it('provides categorized reusable material modules', () => {
    expect(outfitMaterialGroups.map((group) => group.label)).toEqual(['基础视角', '动态展示', '细节卖点', '内容场景'])
    expect(outfitMaterials).toHaveLength(14)
    expect(outfitMaterials.slice(0, 3).map((item) => item.id)).toEqual(['front', 'side', 'back'])
  })

  it('uses selected modules and treats custom text as a shared supplement', () => {
    const materials = resolveOutfitMaterials(['front', 'street'], [], '突出秋季氛围')
    const prompt = buildOutfitPlanPrompt(materials, '突出秋季氛围', { aspectRatio: '3:4', resolution: '2K' })

    expect(materials.map((item) => item.id)).toEqual(['front', 'street'])
    expect(prompt).toContain('统一补充要求：突出秋季氛围')
    expect(prompt).toContain('统一画面规格：3:4，2K')
    expect(prompt).toContain('不描述说话、台词、音效、运镜或连续动作')
  })

  it('creates one custom material when no preset is selected', () => {
    expect(resolveOutfitMaterials([], [], '秋季枫叶小径')).toEqual([
      { id: 'custom', label: '自定义素材', category: 'custom', categoryLabel: '自定义', description: '秋季枫叶小径' },
    ])
  })

  it('parses one prompt for every requested module', () => {
    const materials = resolveOutfitMaterials(['front', 'street'])
    expect(parseOutfitPlan('[{"type":"front","prompt":"正面全身穿搭"},{"type":"street","prompt":"街拍穿搭"}]', materials)).toEqual([
      expect.objectContaining({ id: 'front', category: 'view', prompt: '正面全身穿搭' }),
      expect.objectContaining({ id: 'street', prompt: '街拍穿搭' }),
    ])
  })

  it('maps saved scene selections to the closest material modules', () => {
    expect(resolveOutfitMaterials(undefined, ['studio', 'cafe']).map((item) => item.id)).toEqual(['front', 'date'])
  })
})
