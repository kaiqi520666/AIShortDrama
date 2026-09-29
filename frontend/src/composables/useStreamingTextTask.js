import { i18n } from '../i18n/index'
import { ref } from 'vue'
import { useVueFlow } from '@vue-flow/core'
import { useAuthStore } from '../stores/auth'
import { getApiErrorMessage } from '../utils/apiError'

const { t } = i18n.global

export function useStreamingTextTask(nodeId) {
  const authStore = useAuthStore()
  const { updateNodeData } = useVueFlow()
  const running = ref(false)
  const failure = ref('')
  const partialContent = ref('')

  async function runTextTask(streamer, payload, {
    onSuccess,
    failureMessage = t('canvas.textTaskFailed'),
    preservePartial = false,
  } = {}) {
    if (running.value) return null
    running.value = true
    failure.value = ''
    partialContent.value = ''
    let generatedLocale
    updateNodeData(nodeId, { status: 'generating', generationError: '' })
    try {
      await streamer(
        payload,
        (delta) => {
          partialContent.value += delta
          if (preservePartial) updateNodeData(nodeId, { content: partialContent.value })
        },
        (taskId, meta = {}) => {
          generatedLocale = meta.generated_locale
          updateNodeData(nodeId, {
            generationTaskId: taskId,
            generationStatus: 'running',
            ...(meta.template_version ? { templateVersion: meta.template_version } : {}),
          })
        },
      )
      const result = await onSuccess?.(partialContent.value)
      updateNodeData(nodeId, {
        ...(result || {}),
        ...(generatedLocale ? { generated_locale: generatedLocale } : {}),
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
