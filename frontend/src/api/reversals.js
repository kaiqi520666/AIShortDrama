import { i18n } from '../i18n/index'
import { streamGeneration } from './generations'

const { t } = i18n.global

export function streamReversePrompt(payload, onDelta, onMeta) {
  return streamGeneration('/reversals/stream', payload, onDelta, onMeta, t('canvas.reverseFailed'))
}
