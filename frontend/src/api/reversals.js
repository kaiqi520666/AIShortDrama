import { streamGeneration } from './generations'

export function streamReversePrompt(payload, onDelta, onMeta) {
  return streamGeneration('/reversals/stream', payload, onDelta, onMeta, '反推生成失败')
}
