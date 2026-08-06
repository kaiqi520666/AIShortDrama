import { onBeforeUnmount } from 'vue'

export function useMediaNodeResize({
  getId,
  getType,
  getData,
  getMediaWidth,
  getDisplayAspectRatio,
  getZoom,
  updateNodeData,
}) {
  let resizeState = null

  function resizeNode(event) {
    if (!resizeState) return
    const zoom = getZoom() || 1
    if (resizeState.kind === 'media') {
      updateNodeData(getId(), {
        displayWidth: Math.min(
          720,
          Math.max(
            resizeState.minWidth,
            Math.round(resizeState.width + (event.clientX - resizeState.x) / zoom),
          ),
        ),
      })
      return
    }
    updateNodeData(getId(), {
      width: Math.max(
        resizeState.minWidth,
        Math.round(resizeState.width + (event.clientX - resizeState.x) / zoom),
      ),
      height: Math.max(
        resizeState.minHeight,
        Math.round(resizeState.height + (event.clientY - resizeState.y) / zoom),
      ),
    })
  }

  function stopResize() {
    window.removeEventListener('pointermove', resizeNode)
    window.removeEventListener('pointerup', stopResize)
    resizeState = null
  }

  function startResize(event) {
    stopResize()
    const data = getData()
    const type = getType()
    const mediaWidth = getMediaWidth()
    const audio = type === 'audio'
    resizeState = mediaWidth
      ? {
          kind: 'media',
          x: event.clientX,
          width: data.displayWidth || mediaWidth,
          minWidth: getDisplayAspectRatio() < 0.5 ? 96 : 180,
        }
      : {
          kind: 'free',
          x: event.clientX,
          y: event.clientY,
          width: data.width || (audio ? 360 : 350),
          height: data.height || (audio ? 170 : 220),
          minWidth: 260,
          minHeight: audio ? 120 : 160,
        }
    window.addEventListener('pointermove', resizeNode)
    window.addEventListener('pointerup', stopResize)
  }

  onBeforeUnmount(stopResize)

  return { startResize, stopResize, resizeNode }
}
