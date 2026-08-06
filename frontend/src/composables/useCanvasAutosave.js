import { getCurrentInstance, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

export function useCanvasAutosave({ store, getPayload, getViewport, confirm, delay = 800, eventTarget = globalThis.window }) {
  const dirty = ref(false)
  const enabled = ref(false)
  let timer = null

  function cancelScheduledSave() {
    if (timer !== null) eventTarget?.clearTimeout(timer)
    timer = null
  }

  async function saveNow() {
    cancelScheduledSave()
    if (!dirty.value && store.saveStatus !== 'failed') return true
    try {
      await store.saveCanvas(getViewport?.())
      if (store.saveConflict || store.saveStatus === 'failed') throw new Error('画布保存失败')
      dirty.value = false
      return true
    } catch {
      dirty.value = true
      return false
    }
  }

  function scheduleSave() {
    if (!enabled.value || !store.ready || store.saveConflict) return
    dirty.value = true
    cancelScheduledSave()
    timer = eventTarget?.setTimeout(() => { saveNow() }, delay) ?? null
  }

  async function saveBeforeLeave() {
    if (await saveNow()) return true
    return confirm({
      title: '画布保存失败',
      message: '最新修改尚未保存，仍要离开画布吗？',
      confirmText: '仍然离开',
      cancelText: '留在画布',
      tone: 'danger',
    })
  }

  function retrySave() {
    dirty.value = true
    return saveNow()
  }

  function handleBeforeUnload(event) {
    if (!dirty.value && !['saving', 'failed', 'conflict'].includes(store.saveStatus)) return
    event.preventDefault()
    event.returnValue = ''
  }

  watch(getPayload, scheduleSave, { deep: true })

  if (getCurrentInstance()) {
    onBeforeRouteLeave(saveBeforeLeave)
    onMounted(() => eventTarget?.addEventListener('beforeunload', handleBeforeUnload))
    onBeforeUnmount(() => {
      cancelScheduledSave()
      eventTarget?.removeEventListener('beforeunload', handleBeforeUnload)
    })
  }

  return {
    dirty,
    enable: () => { enabled.value = true },
    scheduleSave,
    saveBeforeLeave,
    retrySave,
    cancelScheduledSave,
    handleBeforeUnload,
  }
}
