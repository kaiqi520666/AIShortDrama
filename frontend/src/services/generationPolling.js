import { getGenerationTask } from '../api/generations'
import { useAuthStore } from '../stores/auth'

const pollTimers = new Map()

function schedulePoll(taskId, nodeId, updateNodeData) {
  pollTimers.set(taskId, window.setTimeout(() => pollTask(taskId, nodeId, updateNodeData), 5000))
}

async function pollTask(taskId, nodeId, updateNodeData) {
  try {
    const result = await getGenerationTask(taskId)
    if (result.code !== 0) throw new Error(result.message)
    const task = result.data
    updateNodeData(nodeId, {
      generationStatus: task.status,
      generationProgress: task.progress,
    })
    if (task.status === 'succeeded') {
      useAuthStore().refreshCredits().catch(() => {})
      const generated = task.result?.data?.[0]
      const asset = generated?.url
      const mediaLabel = { image: '图片', video: '视频', audio: '音频' }[task.task_type] || '内容'
      pollTimers.delete(taskId)
      if (!asset) {
        updateNodeData(nodeId, { status: 'failed', generationError: `任务未返回${mediaLabel}地址` })
        return
      }
      updateNodeData(nodeId, {
        asset,
        ...(generated.asset_id ? { assetId: generated.asset_id } : {}),
        status: 'ready',
        generationProgress: 100,
        generationError: '',
        ...(generated.duration ? { sourceDuration: generated.duration } : {}),
      })
      return
    }
    if (['failed', 'cancelled', 'timeout'].includes(task.status)) {
      useAuthStore().refreshCredits().catch(() => {})
      const mediaLabel = { image: '图片', video: '视频', audio: '音频' }[task.task_type] || '内容'
      pollTimers.delete(taskId)
      updateNodeData(nodeId, {
        status: 'failed',
        generationError: task.error_message || `${mediaLabel}生成失败`,
      })
      return
    }
  } catch {
    schedulePoll(taskId, nodeId, updateNodeData)
    return
  }
  schedulePoll(taskId, nodeId, updateNodeData)
}

export function startGenerationPolling(taskId, nodeId, updateNodeData) {
  if (pollTimers.has(taskId)) return
  pollTimers.set(taskId, null)
  pollTask(taskId, nodeId, updateNodeData)
}
