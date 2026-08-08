export function buildApparelVisualRequest({
  workspaceId,
  nodeId,
  model,
  garmentUrl,
  modelUrl,
  apparelContext,
  aspectRatio,
  resolution,
  templateVersion,
  userRequirement,
}) {
  return {
    workspace_id: workspaceId,
    node_id: nodeId,
    model,
    media_type: 'image',
    media_url: garmentUrl,
    media_urls: [modelUrl],
    response_mode: 'outfit_visual_plan',
    template_key: 'apparel_visual',
    template_version: templateVersion,
    template_context: {
      apparel_context: apparelContext,
      aspect_ratio: aspectRatio,
      resolution,
      reference_count: 2,
      user_requirement: userRequirement || '',
    },
  }
}

export function parseOutfitPrompt(content) {
  const source = String(content || '').trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  const start = source.indexOf('{')
  const end = source.lastIndexOf('}')
  if (start < 0 || end <= start) throw new Error('未生成有效的试穿定妆方案')
  try {
    const prompt = JSON.parse(source.slice(start, end + 1))?.prompt?.trim()
    if (prompt) return prompt
  } catch {
    // Fall through to the stable user-facing error.
  }
  throw new Error('试穿定妆方案格式异常')
}

export function resolveOutfitReference(outfitData = {}, nodes = []) {
  const generated = (outfitData.generatedNodeIds || [])
    .map((id) => nodes.find((node) => node.id === id))
    .filter(Boolean)
  const node = generated.find((item) => item.data.resourceType === 'outfit-reference')
    || (generated.length === 1 && !generated[0].data.outfitMaterialId ? generated[0] : null)
  if (node) return { node, asset: node.data.asset || '', assetId: node.data.assetId || null, legacy: false }
  return {
    node: null,
    asset: outfitData.outfitBoardAsset || '',
    assetId: outfitData.outfitBoardAssetId || null,
    legacy: Boolean(outfitData.outfitBoardAsset),
  }
}
