import { describe, expect, it } from 'vitest'
import { createRequestState, failRequest, finishRequest, isRequestLoading, startRequest } from './requestState'

describe('requestState', () => {
  it('tracks lifecycle and ignores stale completions', () => {
    const state = createRequestState()
    const first = startRequest(state)
    const second = startRequest(state)
    expect(isRequestLoading(state)).toBe(true)
    expect(finishRequest(state, first)).toBe(false)
    expect(state.status).toBe('loading')
    expect(failRequest(state, second, 'failed')).toBe(true)
    expect(state.status).toBe('error')
    expect(state.error).toBe('failed')
  })
})
