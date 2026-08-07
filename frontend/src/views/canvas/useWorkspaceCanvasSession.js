import { ref } from 'vue'
import { getApiErrorMessage } from '../../utils/apiError'

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
    loadingId = loading.showLoading('正在打开工作台…')
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
        const message = getApiErrorMessage(error, '画布配置加载失败')
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
