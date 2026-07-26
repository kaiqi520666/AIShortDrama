import { describe, expect, it } from 'vitest'
import { normalizeAssetItem, systemImageAssets } from './assetLibrary'

describe('asset library', () => {
  it('provides system model assets', () => {
    expect(systemImageAssets).toHaveLength(25)
    expect(systemImageAssets.every((item) => item.category === 'model' && item.source === 'system')).toBe(true)
  })

  it('normalizes existing user assets as general images', () => {
    expect(normalizeAssetItem({ id: 'asset-1', name: '图片', url: 'https://example.com/a.png', media_type: 'image' })).toMatchObject({
      id: 'asset-1', category: 'general', source: 'user', mediaType: 'image',
    })
  })
})
