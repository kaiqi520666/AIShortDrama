import { reactive } from 'vue'

export function createRequestState() {
  return reactive({
    status: 'idle',
    error: '',
    requestId: 0,
  })
}

export function startRequest(state) {
  state.requestId += 1
  state.status = 'loading'
  state.error = ''
  return state.requestId
}

export function finishRequest(state, requestId, status = 'success') {
  if (requestId !== state.requestId) return false
  state.status = status
  return true
}

export function failRequest(state, requestId, error) {
  if (requestId !== state.requestId) return false
  state.status = 'error'
  state.error = error || ''
  return true
}

export function isRequestLoading(state) {
  return state.status === 'loading'
}
