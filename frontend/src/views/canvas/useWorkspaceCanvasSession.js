import { i18n } from '../../i18n/index'
import { ref } from 'vue'
import { getApiErrorMessage } from '../../utils/apiError'

const { t } = i18n.global

function isCancelled(error) {
  return error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError'
}

export function useWorkspaceCanvasSession({ workspaceStore, capabilityStore, contentTemplateStore, loading, toast }) {
  const loadError = ref('')
  let controller = null
  let loadingId = null
  let requestSequence = 0

  function finishLoading() {
    if (!loadingId) return
    loading.hideLoading(loadingId)
    loadingId = null
  }

  function cancelLoad() {
    requestSequence += 1
    controller?.abort()
    controller = null
    finishLoading()
  }

  async function load(workspaceId, { commit = true, initial = false } = {}) {
    cancelLoad()
    const currentSequence = ++requestSequence
    controller = new AbortController()
    loadingId = loading.showLoading(t('canvas.openingWorkspace'))
    loadError.value = ''
    let workspace = null
    try {
      [workspace] = await Promise.all([
        commit
          ? workspaceStore.open(workspaceId, { signal: controller.signal })
          : workspaceStore.fetch(workspaceId, { signal: controller.signal }),
        capabilityStore.load(),
      ])
      if (workspace?.workspace_type === 'ecommerce') await contentTemplateStore.load()
      return currentSequence === requestSequence ? workspace : null
    } catch (error) {
      if (currentSequence === requestSequence && !isCancelled(error)) {
        const message = getApiErrorMessage(error, t('canvas.canvasConfigFailed'))
        if (initial) loadError.value = message
        else toast.error(message)
      }
      return null
    } finally {
      if (currentSequence === requestSequence) {
        controller = null
        if (!workspace) finishLoading()
      }
    }
  }

  function dispose() {
    cancelLoad()
  }

  return {
    loadError,
    load,
    finishLoading,
    dispose,
  }
}
