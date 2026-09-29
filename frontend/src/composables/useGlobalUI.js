import { readonly, ref } from 'vue'

const toasts = ref([])
const confirmState = ref(null)
const promptState = ref(null)
const toastTimers = new Map()
let confirmResolver = null
let promptResolver = null

function removeToast(id) {
  window.clearTimeout(toastTimers.get(id))
  toastTimers.delete(id)
  toasts.value = toasts.value.filter((item) => item.id !== id)
}

function showToast(message, type = 'info', duration = 3200) {
  const id = crypto.randomUUID()
  toasts.value = [...toasts.value.slice(-3), { id, message, type }]
  if (duration > 0) toastTimers.set(id, window.setTimeout(() => removeToast(id), duration))
  return id
}

function settleConfirm(result) {
  confirmResolver?.(result)
  confirmResolver = null
  confirmState.value = null
}

function confirm(options) {
  if (confirmResolver) settleConfirm(false)
  confirmState.value = {
    title: '',
    message: '',
    confirmText: '',
    cancelText: '',
    tone: 'default',
    ...options,
  }
  return new Promise((resolve) => { confirmResolver = resolve })
}

function settlePrompt(result) {
  promptResolver?.(result)
  promptResolver = null
  promptState.value = null
}

function prompt(options) {
  if (promptResolver) settlePrompt(null)
  promptState.value = {
    title: '',
    message: '',
    value: '',
    placeholder: '',
    confirmText: '',
    cancelText: '',
    maxLength: 100,
    ...options,
  }
  return new Promise((resolve) => { promptResolver = resolve })
}

export function useGlobalToast() {
  return {
    toasts: readonly(toasts),
    removeToast,
    show: showToast,
    success: (message, duration) => showToast(message, 'success', duration),
    error: (message, duration) => showToast(message, 'error', duration ?? 5000),
    warning: (message, duration) => showToast(message, 'warning', duration),
    info: (message, duration) => showToast(message, 'info', duration),
  }
}

export function useGlobalConfirm() {
  return {
    confirmState: readonly(confirmState),
    confirm,
    acceptConfirm: () => settleConfirm(true),
    cancelConfirm: () => settleConfirm(false),
  }
}

export function useGlobalPrompt() {
  return {
    promptState: readonly(promptState),
    prompt,
    acceptPrompt: settlePrompt,
    cancelPrompt: () => settlePrompt(null),
  }
}
