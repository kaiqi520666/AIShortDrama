import { getCurrentInstance, onBeforeUnmount, onMounted } from 'vue'

export function useCanvasShortcuts({
  canvasTool,
  pointerMode,
  shortcutPanelOpen,
  selectedNodes,
  generationPanel,
  openCreateMenu,
  selectTool,
  fitView,
  undo,
  redo,
  groupSelected,
  ungroupSelected,
  duplicateSelected,
  connectSelected,
  deleteSelected,
  zoomIn,
  zoomOut,
  eventTarget = globalThis.window,
}) {
  let toolBeforeSpace = null

  function handleKeydown(event) {
    if (event.target instanceof Element && event.target.closest('input, textarea, [contenteditable]:not([contenteditable="false"])')) return
    const key = event.key.toLowerCase()
    const command = event.ctrlKey || event.metaKey
    if (key === 'escape' && shortcutPanelOpen.value) {
      shortcutPanelOpen.value = false
      return
    }
    if (shortcutPanelOpen.value) return
    if (event.code === 'Space' && !command && !event.altKey) {
      event.preventDefault()
      if (toolBeforeSpace === null) {
        toolBeforeSpace = canvasTool.value
        canvasTool.value = 'hand'
      }
      return
    }
    if (key === 'tab' && !command && !event.altKey) {
      event.preventDefault()
      openCreateMenu()
      return
    }
    if (!command && !event.altKey && (key === 'v' || key === 'h')) {
      event.preventDefault()
      selectTool(key === 'h' ? 'hand' : 'move')
      return
    }
    if (event.altKey && event.shiftKey && key === 'f') {
      event.preventDefault()
      fitView({ padding: 0.24, duration: 350 })
      return
    }
    if (!command && !event.altKey && (key === 'backspace' || key === 'delete')) {
      event.preventDefault()
      return deleteSelected?.()
    }
    if (!command || event.altKey) return
    if (['z', 'y', 'g', 'd', 'l', 'enter', '0', '=', '+', '-'].includes(key)) event.preventDefault()
    if (key === 'z') return event.shiftKey ? redo() : undo()
    if (key === 'y') return redo()
    if (key === 'g') return event.shiftKey ? ungroupSelected() : (selectedNodes.value.length > 1 && groupSelected())
    if (key === 'd') return selectedNodes.value.length && duplicateSelected()
    if (key === 'l') return connectSelected()
    if (key === 'enter') return generationPanel.value?.submitTask?.()
    if (key === '0') return fitView({ padding: 0.24, duration: 350 })
    if (key === '=' || key === '+') return zoomIn({ duration: 180 })
    if (key === '-') zoomOut({ duration: 180 })
  }

  function restoreTemporaryHand() {
    if (toolBeforeSpace === null) return
    canvasTool.value = toolBeforeSpace
    toolBeforeSpace = null
    pointerMode.value = null
  }

  function handleKeyup(event) {
    if (event.code === 'Space') restoreTemporaryHand()
  }

  if (getCurrentInstance()) {
    onMounted(() => {
      eventTarget?.addEventListener('keydown', handleKeydown)
      eventTarget?.addEventListener('keyup', handleKeyup)
      eventTarget?.addEventListener('blur', restoreTemporaryHand)
    })
    onBeforeUnmount(() => {
      eventTarget?.removeEventListener('keydown', handleKeydown)
      eventTarget?.removeEventListener('keyup', handleKeyup)
      eventTarget?.removeEventListener('blur', restoreTemporaryHand)
    })
  }

  return { handleKeydown, handleKeyup, restoreTemporaryHand }
}
