import { parseProductStoryboardPlan } from './productStoryboard'

export function buildOutfitStoryboardRequest({
  workspaceId,
  nodeId,
  model,
  template,
  outfitReferenceUrl,
  garmentUrl,
  modelUrl,
  sceneUrl,
  apparelContext,
  duration,
  videoAspectRatio,
  userRequirement,
}) {
  const references = [outfitReferenceUrl, garmentUrl, modelUrl, ...(sceneUrl ? [sceneUrl] : [])]
  return {
    workspace_id: workspaceId,
    node_id: nodeId,
    model,
    media_type: 'image',
    media_url: references[0],
    media_urls: references.slice(1),
    template_key: 'apparel_showcase',
    template_version: template.version,
    template_context: {
      apparel_context: apparelContext,
      duration,
      video_aspect_ratio: videoAspectRatio,
      scene_count: sceneUrl ? 1 : 0,
      user_requirement: userRequirement || '',
    },
    response_mode: 'apparel_storyboard_plan',
  }
}

export function parseOutfitStoryboardPlan(content, template) {
  return parseProductStoryboardPlan(content, template)
}
