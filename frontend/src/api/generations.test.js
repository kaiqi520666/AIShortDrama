import { afterEach, describe, expect, it, vi } from 'vitest'
import { streamTextGeneration } from './generations'
import { streamReversePrompt } from './reversals'
import { i18n } from '../i18n'

afterEach(() => {
  vi.unstubAllGlobals()
  i18n.global.locale.value = 'id'
})

describe('localized stream errors', () => {
  it.each(['zh-CN', 'id'])('sends current language on both AI endpoints: %s', async (locale) => {
    i18n.global.locale.value = locale
    const fetch = vi.fn().mockImplementation(() => Promise.resolve(new Response('{"type":"done"}\n')))
    vi.stubGlobal('fetch', fetch)
    const payload = { prompt: '保留原文' }
    await streamTextGeneration(payload, vi.fn())
    await streamReversePrompt(payload, vi.fn())
    for (const [, request] of fetch.mock.calls) {
      expect(JSON.parse(request.body)).toEqual({ ...payload, locale })
    }
    expect(payload).not.toHaveProperty('locale')
  })
  it('translates non-2xx errors and preserves the request prompt', async () => {
    const fetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({
      code: 1, error_key: 'insufficient_credits', message: '积分不足',
    }), { status: 402 }))
    vi.stubGlobal('fetch', fetch)
    const payload = { prompt: '保留用户提示词', model: 'test-model' }
    await expect(streamTextGeneration(payload, vi.fn())).rejects.toThrow(i18n.global.t('errors.insufficient_credits'))
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ ...payload, locale: i18n.global.locale.value })
  })

  it('translates stream errors without translating deltas or metadata', async () => {
    const events = [
      { type: 'meta', task_id: 'task-1' },
      { type: 'delta', content: '生成内容保持中文' },
      { type: 'error', error_key: 'upstream_unavailable', message: '上游原文' },
    ]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(events.map(JSON.stringify).join('\n'))))
    const delta = vi.fn()
    const meta = vi.fn()
    await expect(streamTextGeneration({}, delta, meta)).rejects.toThrow(i18n.global.t('errors.upstream_unavailable'))
    expect(delta).toHaveBeenCalledWith('生成内容保持中文')
    expect(meta).toHaveBeenCalledWith('task-1', events[0])
  })

  it('uses localized fallback for legacy stream errors and network failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"type":"error","message":"旧错误"}\n')))
    await expect(streamTextGeneration({}, vi.fn())).rejects.toThrow(i18n.global.t('errors.request_failed'))
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))
    await expect(streamTextGeneration({}, vi.fn())).rejects.toThrow(i18n.global.t('errors.network_error'))
  })
})
