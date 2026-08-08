import { describe, expect, it } from 'vitest'
import { buildApparelVisualRequest, parseOutfitPlan, resolveOutfitMaterials } from './outfit'
import { contentTemplatesFixture } from '../../test/contentTemplates'

const template = contentTemplatesFixture.apparel_visual

describe('outfit planning', () => {
  it('derives the fixed six views from the apparel visual template', () => {
    const materials = resolveOutfitMaterials(template)
    expect(materials).toHaveLength(6)
    expect(materials.map((item) => item.id)).toEqual(['front', 'three-quarter', 'back', 'turn', 'fabric', 'lifestyle'])
    expect(materials[0]).toEqual(expect.objectContaining({ label: '正面全身', categoryLabel: '六视角试穿' }))
  })

  it('builds a structured server-template request without a prompt', () => {
    const request = buildApparelVisualRequest({
      workspaceId: 'workspace-1',
      nodeId: 'outfit-1',
      model: 'gpt-5.6-sol',
      garmentUrl: 'https://example.com/garment.png',
      modelUrl: 'https://example.com/model.png',
      apparelContext: '单品1：白色衬衫',
      selectedViewIds: ['front', 'back'],
      aspectRatio: '9:16',
      resolution: '1K',
      templateVersion: 3,
      userRequirement: '自然日光',
    })
    expect(request).not.toHaveProperty('prompt')
    expect(request.template_key).toBe('apparel_visual')
    expect(request.template_context).toEqual(expect.objectContaining({
      selected_view_ids: ['front', 'back'],
      reference_count: 2,
      user_requirement: '自然日光',
    }))
  })

  it('parses one prompt for every requested view', () => {
    const materials = resolveOutfitMaterials(template)
    const content = JSON.stringify(materials.map((item) => ({ id: item.id, prompt: `${item.label}试穿` })))
    expect(parseOutfitPlan(content, materials)).toHaveLength(6)
    expect(parseOutfitPlan(content, materials)[0]).toEqual(expect.objectContaining({ id: 'front', prompt: '正面全身试穿' }))
  })
})
