import { i18n } from '../i18n/index'
import { apiClient } from './client'
import { createApiError } from '../utils/apiError'

const { t } = i18n.global

export async function getGenerationCapabilities() {
  return (await apiClient.get('/generations/capabilities')).data
}

export async function createImageGeneration(payload) {
  return (await apiClient.post('/generations/images', payload)).data
}

export async function createVideoGeneration(payload) {
  return (await apiClient.post('/generations/videos', payload)).data
}

export async function createAudioGeneration(payload) {
  return (await apiClient.post('/generations/audios', payload)).data
}

export async function streamGeneration(path, payload, onDelta, onMeta, errorLabel) {
  const response = await fetch(`/api${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).catch(() => { throw createApiError({ error_key: 'network_error' }) })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw createApiError(error, response.status)
  }
  if (!response.body) throw new Error(t('canvas.streamUnsupported'))

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let completed = false

  function consume(line) {
    if (!line) return
    const event = JSON.parse(line)
    if (event.type === 'meta') onMeta?.(event.task_id, event)
    else if (event.type === 'delta') onDelta(event.content)
    else if (event.type === 'error') throw createApiError(event)
    else if (event.type === 'done') completed = true
  }

  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
      const lines = buffer.split('\n')
      buffer = lines.pop()
      lines.forEach(consume)
      if (done) break
    }
    consume(buffer)
    if (!completed) throw new Error(t('canvas.streamInterrupted'))
  } catch (error) {
    await reader.cancel().catch(() => {})
    throw error
  } finally {
    reader.releaseLock()
  }
}

export function streamTextGeneration(payload, onDelta, onMeta) {
  return streamGeneration('/generations/texts', payload, onDelta, onMeta, t('canvas.textGenerationFailed'))
}

export async function getGenerationTask(taskId, config) {
  return (await apiClient.get(`/generations/${taskId}`, config)).data
}
