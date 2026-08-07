import { ref } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { useAuthStore } from '../stores/auth'
import { getApiErrorMessage } from '../utils/apiError'

export function useStreamingTextTask(nodeId) {
  const authStore = useAuthStore()
  const { updateNodeData } = useVueFlow()
  const running = ref(false)
  const failure = ref('')
  const partialContent = ref('')

  async function runTextTask(streamer, payload, {
    onSuccess,
    failureMessage = '文本任务生成失败',
    preservePartial = false,
  } = {}) {
    if (running.value) return null
    running.value = true
    failure.value = ''
    partialContent.value = ''
    updateNodeData(nodeId, { status: 'generating', generationError: '' })
    try {
      await streamer(
        payload,
        (delta) => {
          partialContent.value += delta
          if (preservePartial) updateNodeData(nodeId, { content: partialContent.value })
        },
        (taskId, meta = {}) => updateNodeData(nodeId, {
          generationTaskId: taskId,
          generationStatus: 'running',
          ...(meta.template_version ? { templateVersion: meta.template_version } : {}),
        }),
      )
      const result = await onSuccess?.(partialContent.value)
      updateNodeData(nodeId, {
        ...(result || {}),
        status: 'ready',
        generationStatus: 'succeeded',
        generationError: '',
      })
      return partialContent.value
    } catch (error) {
      failure.value = getApiErrorMessage(error, failureMessage)
      updateNodeData(nodeId, {
        status: 'failed',
        generationStatus: 'failed',
        generationError: failure.value,
        ...(preservePartial ? { content: partialContent.value } : {}),
      })
      return null
    } finally {
      running.value = false
      await authStore.refreshCredits().catch(() => {})
    }
  }

  return { running, failure, partialContent, runTextTask }
}
