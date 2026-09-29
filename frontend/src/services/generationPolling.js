import { i18n } from '../i18n/index'
import { getGenerationTask } from '../api/generations'
import { useAuthStore } from '../stores/auth'
import { useCanvasStore } from '../stores/canvas'
import { getApiErrorMessage, getTaskErrorMessage } from '../utils/apiError'

const { t } = i18n.global

const POLL_INTERVAL = 5000
const RETRY_DELAYS = [5000, 10000, 20000, 40000, 60000, 60000]
const MAX_POLL_DURATION = 30 * 60 * 1000
const polls = new Map()

const mediaLabels = { image: 'canvas.image', video: 'canvas.video', audio: 'canvas.audio' }

function clearRecord(record) {
  if (record.timer !== null) globalThis.clearTimeout(record.timer)
  record.controller?.abort()
  record.timer = null
  record.controller = null
  if (polls.get(record.taskId) === record) polls.delete(record.taskId)
}

function schedule(record, delay = POLL_INTERVAL) {
  if (polls.get(record.taskId) !== record) return
  record.timer = globalThis.setTimeout(() => pollTask(record), delay)
}

function failNode(record, message) {
  clearRecord(record)
  record.updateNodeData(record.nodeId, {
    status: 'failed',
    generationPollingPaused: false,
    generationError: message,
  })
}

function pauseNode(record, message = t('canvas.syncInterruptedResume')) {
  clearRecord(record)
  record.updateNodeData(record.nodeId, {
    generationPollingPaused: true,
    generationError: message,
  })
}

async function pollTask(record) {
  if (polls.get(record.taskId) !== record) return
  if (Date.now() - record.startedAt >= MAX_POLL_DURATION) {
    pauseNode(record, t('canvas.syncTimedOut'))
    return
  }

  record.controller = new AbortController()
  try {
    const result = await getGenerationTask(record.taskId, { signal: record.controller.signal })
    if (polls.get(record.taskId) !== record) return
    if (result.code !== 0) {
      failNode(record, getApiErrorMessage(result))
      return
    }
    record.failures = 0
    const task = result.data
    record.updateNodeData(record.nodeId, {
      generationStatus: task.status,
      generationProgress: task.progress,
      generationPollingPaused: false,
    })
    if (task.status === 'succeeded') {
      useAuthStore().refreshCredits().catch(() => {})
      if (task.result?.type === 'text') {
        clearRecord(record)
        record.updateNodeData(record.nodeId, {
          content: task.result.content || '',
          status: 'ready',
          generationProgress: 100,
          generationError: '',
        })
        return
      }
      const generated = task.result?.data?.[0]
      const asset = generated?.url
      const mediaLabel = t(mediaLabels[task.task_type] || 'canvas.content')
      if (!asset) {
        failNode(record, t('canvas.missingMediaUrl', { p0: mediaLabel }))
        return
      }
      clearRecord(record)
      record.updateNodeData(record.nodeId, {
        asset,
        ...(generated.asset_id ? { assetId: generated.asset_id } : {}),
        status: 'ready',
        generationProgress: 100,
        generationError: '',
        ...(generated.duration ? { sourceDuration: generated.duration } : {}),
        ...(task.task_type === 'video' && task.result?.last_frame_url ? { lastFrameUrl: task.result.last_frame_url } : {}),
      })
      if (task.task_type === 'image') useCanvasStore().unlockStoryboardVideo(record.nodeId)
      return
    }
    if (['failed', 'cancelled', 'timeout'].includes(task.status)) {
      useAuthStore().refreshCredits().catch(() => {})
      failNode(record, getTaskErrorMessage(task))
      return
    }
  } catch (error) {
    if (error.code === 'ERR_CANCELED' || polls.get(record.taskId) !== record) return
    const status = error.response?.status
    if (status === 401) stopAllGenerationPolling()
    if (status && status < 500) {
      failNode(record, getApiErrorMessage(error, t('canvas.taskStatusFailed')))
      return
    }
    record.failures += 1
    if (record.failures >= RETRY_DELAYS.length) {
      pauseNode(record)
      return
    }
    schedule(record, RETRY_DELAYS[record.failures - 1])
    return
  } finally {
    record.controller = null
  }
  schedule(record)
}

export function startGenerationPolling(taskId, nodeId, updateNodeData, workspaceId = useCanvasStore().workspaceId) {
  if (!taskId || polls.has(taskId)) return
  const record = {
    taskId,
    nodeId,
    workspaceId,
    updateNodeData,
    timer: null,
    controller: null,
    startedAt: Date.now(),
    failures: 0,
  }
  polls.set(taskId, record)
  pollTask(record)
}

export function stopGenerationPolling(taskId) {
  const record = polls.get(taskId)
  if (record) clearRecord(record)
}

export function stopWorkspaceGenerationPolling(workspaceId) {
  for (const record of [...polls.values()]) {
    if (record.workspaceId === workspaceId) clearRecord(record)
  }
}

export function stopAllGenerationPolling() {
  for (const record of [...polls.values()]) clearRecord(record)
}
