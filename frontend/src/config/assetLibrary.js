export function normalizeLibraryItem(item, resourceType = 'asset') {
  const type = item.resource_type || resourceType
  const seedance = item.metadata?.seedance || {}
  return {
    id: item.id,
    assetId: type === 'asset' ? item.id : null,
    name: item.name,
    url: item.url,
    mediaType: item.media_type || 'image',
    resourceType: type,
    source: item.source || 'user',
    width: item.width || (type === 'model' ? 3 : null),
    height: item.height || (type === 'model' ? 4 : null),
    byteSize: item.byte_size,
    metadata: item.metadata || {},
    seedanceStatus: type === 'character' ? seedance.status || 'unregistered' : seedance.status || null,
    seedanceAssetUrl: seedance.asset_url || '',
    seedanceGroupId: seedance.group_id || '',
  }
}
