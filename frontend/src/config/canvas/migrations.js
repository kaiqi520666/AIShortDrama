import { createStoryboardTemplates } from './productStoryboard'

export const CURRENT_CANVAS_SCHEMA_VERSION = 2

export function migrateCanvas(source = {}, defaultTextModelId, templates) {
  const canvas = JSON.parse(JSON.stringify(source || {}))
  const version = Number(canvas.schema_version || 1)
  if (version > CURRENT_CANVAS_SCHEMA_VERSION) {
    throw new Error(`画布版本 ${version} 高于当前支持版本 ${CURRENT_CANVAS_SCHEMA_VERSION}`)
  }
  const storyboardTemplate = templates?.product_storyboard
  if (version < 2) {
    canvas.nodes = (canvas.nodes || []).map((node) => node.type === 'product_storyboard'
      ? {
          ...node,
          data: {
            ...node.data,
            textModel: node.data?.textModel ?? defaultTextModelId,
            templateId: node.data?.templateId ?? 'ugc-seeding',
            ...(node.data?.templates || !storyboardTemplate
              ? {}
              : { templates: createStoryboardTemplates(storyboardTemplate) }),
            ...(node.data?.templateVersion != null || !storyboardTemplate
              ? {}
              : { templateVersion: storyboardTemplate.version }),
          },
        }
      : node)
  }
  canvas.schema_version = CURRENT_CANVAS_SCHEMA_VERSION
  return canvas
}
