import { createStoryboardTemplates } from './productStoryboard'
import { defaultReverseModel } from '../reverseModels'

export const CURRENT_CANVAS_SCHEMA_VERSION = 2

export function migrateCanvas(source = {}) {
  const canvas = JSON.parse(JSON.stringify(source || {}))
  const version = Number(canvas.schema_version || 1)
  if (version > CURRENT_CANVAS_SCHEMA_VERSION) {
    throw new Error(`画布版本 ${version} 高于当前支持版本 ${CURRENT_CANVAS_SCHEMA_VERSION}`)
  }
  if (version < 2) {
    canvas.nodes = (canvas.nodes || []).map((node) => node.type === 'product_storyboard'
      ? {
          ...node,
          data: {
            ...node.data,
            textModel: node.data?.textModel ?? defaultReverseModel.id,
            templateId: node.data?.templateId ?? 'ugc-seeding',
            templates: node.data?.templates ?? createStoryboardTemplates(),
          },
        }
      : node)
  }
  canvas.schema_version = CURRENT_CANVAS_SCHEMA_VERSION
  return canvas
}
