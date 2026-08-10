import { describe, expect, it } from 'vitest'
import { buildApparelVisualRequest, parseOutfitPrompt, resolveOutfitReference } from './outfit'

describe('outfit planning', () => {
  it('builds one structured server-template request without a prompt', () => {
    const request = buildApparelVisualRequest({
      workspaceId: 'workspace-1',
      nodeId: 'outfit-1',
      model: 'gpt-5.6-sol',
      garmentUrl: 'https://example.com/garment.png',
      modelUrl: 'https://example.com/model.png',
      apparelContext: '单品1：白色衬衫',
      aspectRatio: '9:16',
      resolution: '1K',
      templateVersion: 2,
      userRequirement: '自然日光',
    })
    expect(request).not.toHaveProperty('prompt')
    expect(request.template_key).toBe('apparel_visual')
    expect(request.template_context).toEqual({
      apparel_context: '单品1：白色衬衫',
      aspect_ratio: '9:16',
      resolution: '1K',
      reference_count: 2,
      model_reference_provided: true,
      scene_reference_provided: false,
      user_requirement: '自然日光',
    })
  })

  it('parses one try-on prompt', () => {
    expect(parseOutfitPrompt('```json\n{"prompt":"正面全身试穿定妆图"}\n```')).toBe('正面全身试穿定妆图')
    expect(() => parseOutfitPrompt('{"items":[]}')).toThrow('试穿定妆方案格式异常')
  })

  it('resolves the current image and falls back to legacy boards', () => {
    const node = { id: 'image-2', data: { resourceType: 'outfit-reference', asset: 'https://example.com/current.png', assetId: 'asset-2' } }
    expect(resolveOutfitReference({ generatedNodeIds: ['image-2'] }, [node])).toEqual({ node, asset: 'https://example.com/current.png', assetId: 'asset-2', legacy: false })
    expect(resolveOutfitReference({ outfitBoardAsset: 'https://example.com/legacy.png', outfitBoardAssetId: 'legacy-1', generatedNodeIds: ['old-1', 'old-2'] }, [])).toEqual({ node: null, asset: 'https://example.com/legacy.png', assetId: 'legacy-1', legacy: true })
  })
})
