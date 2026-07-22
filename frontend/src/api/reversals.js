export async function streamReversePrompt(payload, onDelta, onMeta) {
  const response = await fetch('/api/reversals/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.message || `反推请求失败（${response.status}）`)
  }
  if (!response.body) throw new Error('浏览器不支持流式响应')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let completed = false

  function consume(line) {
    if (!line) return
    const event = JSON.parse(line)
    if (event.type === 'meta') onMeta?.(event.task_id)
    else if (event.type === 'delta') onDelta(event.content)
    else if (event.type === 'error') throw new Error(event.message || '反推生成失败')
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
    if (!completed) throw new Error('反推流式响应异常中断')
  } catch (error) {
    await reader.cancel().catch(() => {})
    throw error
  } finally {
    reader.releaseLock()
  }
}
