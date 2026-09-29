import { i18n } from '../../i18n/index'
import { canvasLabel } from '../../i18n/canvas'
import { getNodeDescriptor } from './nodeCatalog'
import { isNodeTypeAvailable } from './nodePacks'

const { t } = i18n.global

export const maxProductReferenceImages = getNodeDescriptor('product').inputLimits.image.max

export function canConnect(sourceType, targetType, workspaceType = 'general') {
  if (!isNodeTypeAvailable(workspaceType, sourceType) || !isNodeTypeAvailable(workspaceType, targetType)) return false
  const source = getNodeDescriptor(sourceType)
  const target = getNodeDescriptor(targetType)
  return source.outputs.includes(targetType) && target.inputs.includes(sourceType)
}

export function getConnectionError(sourceType, targetType, incomingTypes = [], workspaceType = 'general', targetHandle = '', incomingConnections = []) {
  if (!canConnect(sourceType, targetType, workspaceType)) return t('canvas.incompatibleNodes')
  const limit = getNodeDescriptor(targetType).inputLimits?.[sourceType]
  if (limit && incomingTypes.filter((type) => type === sourceType).length >= limit.max) return canvasLabel(limit.message)
  if (targetType !== 'audio' || !['image', 'audio'].includes(sourceType)) return ''
  if (sourceType === 'image' && incomingTypes.includes('audio')) return t('canvas.mixedAudioImage')
  if (sourceType === 'audio' && incomingTypes.includes('image')) return t('canvas.mixedAudioImage')
  return ''
}

export function inferTargetHandle() {
  return undefined
}
