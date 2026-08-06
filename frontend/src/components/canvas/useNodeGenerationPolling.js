import { onBeforeUnmount, watch } from 'vue'
import { startGenerationPolling, stopGenerationPolling } from '../../services/generationPolling'

export function useNodeGenerationPolling({
  getId,
  getData,
  getWorkspaceId,
  updateNodeData,
}) {
  function stop(taskId = getData().generationTaskId) {
    if (taskId) stopGenerationPolling(taskId)
  }

  function start(taskId = getData().generationTaskId) {
    if (!taskId) return
    startGenerationPolling(taskId, getId(), updateNodeData, getWorkspaceId())
  }

  function resume() {
    updateNodeData(getId(), { generationPollingPaused: false, generationError: '' })
    start()
  }

  watch(
    () => [getData().generationTaskId, getData().status, getData().generationPollingPaused],
    ([taskId, status, paused], [previousTaskId] = []) => {
      if (previousTaskId && previousTaskId !== taskId) stop(previousTaskId)
      if (taskId && status === 'generating' && !paused) start(taskId)
    },
    { immediate: true },
  )

  onBeforeUnmount(() => stop())

  return { start, stop, resume }
}
