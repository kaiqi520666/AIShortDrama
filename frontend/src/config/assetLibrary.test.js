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
  })
})
