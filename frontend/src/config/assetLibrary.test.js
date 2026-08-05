import { describe, expect, it } from 'vitest'
import { normalizeLibraryItem } from './assetLibrary'

describe('asset library', () => {
  it('normalizes assets without mixing reference resource types', () => {
    expect(normalizeLibraryItem({ id: 'asset-1', name: '图片', url: 'https://example.com/a.png', media_type: 'image' })).toMatchObject({
      id: 'asset-1', assetId: 'asset-1', resourceType: 'asset', source: 'user', mediaType: 'image',
    })
    expect(normalizeLibraryItem({ id: 'model-1', resource_type: 'model', source: 'system', name: '模特', url: 'https://example.com/model.png' })).toMatchObject({
      id: 'model-1', assetId: null, resourceType: 'model', source: 'system', width: 3, height: 4,
    })
    expect(normalizeLibraryItem({ id: 'garment-1', resource_type: 'garment', source: 'system', name: '服饰', url: 'https://example.com/garment.png', width: 800, height: 1000 })).toMatchObject({
      id: 'garment-1', assetId: null, resourceType: 'garment', source: 'system', width: 800, height: 1000,
    })
    expect(normalizeLibraryItem({ id: 'character-1', resource_type: 'character', name: '角色', url: 'https://example.com/character.png', metadata: { seedance: { status: 'active', asset_url: 'asset://pa_test' } } })).toMatchObject({
      id: 'character-1', resourceType: 'character', seedanceStatus: 'active', seedanceAssetUrl: 'asset://pa_test',
    })
    expect(normalizeLibraryItem({ id: 'asset-2', name: '普通图片', url: 'https://example.com/asset.png', metadata: { seedance: { status: 'processing', asset_url: 'asset://pa_asset', group_id: 'group-1' } } })).toMatchObject({
      id: 'asset-2', resourceType: 'asset', seedanceStatus: 'processing', seedanceAssetUrl: 'asset://pa_asset', seedanceGroupId: 'group-1',
    })
  })
})
