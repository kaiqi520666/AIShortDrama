import { describe, expect, it } from 'vitest'
import { buildOutfitPlanPrompt, outfitScenes, parseOutfitPlan, resolveOutfitScenes } from './outfit'

describe('outfit planning', () => {
  it('provides nine complementary preset scenes', () => {
    expect(outfitScenes).toHaveLength(9)
    expect(outfitScenes.slice(-3).map((scene) => scene.id)).toEqual(['office', 'party', 'gallery'])
  })

  it('uses selected presets and treats custom text as a shared supplement', () => {
    const scenes = resolveOutfitScenes(['studio', 'street'], '突出秋季氛围')
    const prompt = buildOutfitPlanPrompt(scenes, '突出秋季氛围', { aspectRatio: '3:4', resolution: '2K' })

    expect(scenes.map((scene) => scene.id)).toEqual(['studio', 'street'])
    expect(prompt).toContain('所有场景的补充要求：突出秋季氛围')
    expect(prompt).toContain('统一画面规格：3:4，2K')
  })

  it('creates one custom scene when no preset is selected', () => {
    expect(resolveOutfitScenes([], '秋季枫叶小径')).toEqual([
      { id: 'custom', label: '自定义场景', description: '秋季枫叶小径' },
    ])
  })

  it('parses one prompt for every requested scene', () => {
    const scenes = resolveOutfitScenes(['studio', 'street'])
    expect(parseOutfitPlan('[{"type":"studio","prompt":"棚拍穿搭"},{"type":"street","prompt":"街拍穿搭"}]', scenes)).toEqual([
      expect.objectContaining({ id: 'studio', prompt: '棚拍穿搭' }),
      expect.objectContaining({ id: 'street', prompt: '街拍穿搭' }),
    ])
  })
})
