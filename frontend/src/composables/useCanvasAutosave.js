import { i18n } from '../i18n/index'
import { getCurrentInstance, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

const { t } = i18n.global

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
      if (store.saveConflict || store.saveStatus === 'failed') throw new Error(t('canvas.canvasSaveFailed'))
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
      title: t('canvas.canvasSaveFailed'),
      message: t('canvas.leaveUnsavedConfirm'),
      confirmText: t('canvas.leaveAnyway'),
      cancelText: t('canvas.stayOnCanvas'),
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
