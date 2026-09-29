import { i18n } from '../../i18n/index'
import { canvasLabel } from '../../i18n/canvas'
import { nextTick, ref } from 'vue'
import { uploadMedia } from '../../api/uploads'
import { getNodeDescriptor } from '../../config/canvas/nodeCatalog'
import { getApiErrorMessage } from '../../utils/apiError'
import { mediaUploadRules, readMediaMetadata } from '../../utils/mediaFiles'

const { t } = i18n.global

export const uploadRules = {
  image: { ...mediaUploadRules.image, accept: 'image/jpeg,image/png,image/webp' },
  video: { ...mediaUploadRules.video, accept: 'video/mp4,video/quicktime,video/webm' },
  audio: { ...mediaUploadRules.audio, accept: 'audio/mpeg,audio/wav,audio/x-wav,audio/mp4' },
}

export function validateUploadFile(type, file) {
  const rule = uploadRules[type]
  if (!rule) return t('canvas.unsupportedUploadType')
  if (!rule.types.includes(file.type)) return t('canvas.unsupportedMediaFormat', { p0: canvasLabel(getNodeDescriptor(type).label) })
  if (file.size > rule.maxSize) return t('canvas.fileSizeLimit', { p0: rule.maxSize / 1024 / 1024 })
  return ''
}

export function useCanvasDropUpload({ store, nodes, contextMenu, activeGroupId, screenToFlowCoordinate, updateNodeData, toast }) {
  const canvasDropActive = ref(false)
  const uploadInput = ref(null)
  const pendingUpload = ref(null)

  function handleCanvasDragOver(event) {
    if (!event.dataTransfer.types.includes('application/x-mooncut-canvas-item')) return
    event.preventDefault()
    event.dataTransfer.dropEffect = 'copy'
    canvasDropActive.value = true
  }

  function handleCanvasDragLeave(event) {
    if (!event.currentTarget.contains(event.relatedTarget)) canvasDropActive.value = false
  }

  function handleCanvasDrop(event) {
    const raw = event.dataTransfer.getData('application/x-mooncut-canvas-item')
    canvasDropActive.value = false
    if (!raw) return
    event.preventDefault()
    try {
      const item = JSON.parse(raw)
      if (item.kind !== 'asset') return
      store.addAssetNode(item.asset, screenToFlowCoordinate({ x: event.clientX, y: event.clientY }))
      activeGroupId.value = null
    } catch {
      toast.error(t('canvas.dropFailed'))
    }
  }

  function chooseUpload(type) {
    pendingUpload.value = { type, position: contextMenu.value.position }
    contextMenu.value = null
    nextTick(() => uploadInput.value?.click())
  }

  async function handlePaneUpload(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    const upload = pendingUpload.value
    pendingUpload.value = null
    if (!file || !upload) return
    const validationError = validateUploadFile(upload.type, file)
    if (validationError) return toast.warning(validationError)

    const id = store.addNode(upload.type, upload.position)
    const node = nodes.value.find((item) => item.id === id)
    node.data = { ...node.data, status: 'uploading', assetSource: 'upload', pasted: true }
    try {
      const metadata = await readMediaMetadata(upload.type, file)
      const result = await uploadMedia(upload.type, file, { workspaceId: store.workspaceId, nodeId: id, timeout: 60_000, ...metadata })
      if (result.code !== 0) throw new Error(result.message)
      const sourceWidth = result.data.width || metadata.width
      const sourceHeight = result.data.height || metadata.height
      updateNodeData(id, {
        asset: result.data.url,
        assetId: result.data.id,
        status: 'ready',
        ...(sourceWidth ? { sourceWidth, sourceHeight, sourceAspectRatio: sourceWidth / sourceHeight } : {}),
        ...(metadata.duration ? { sourceDuration: metadata.duration } : {}),
        sourceByteSize: result.data.size,
      })
    } catch (error) {
      store.deleteNode(id)
      toast.error(error.code === 'ECONNABORTED' ? t('canvas.uploadTimeout') : getApiErrorMessage(error, t('canvas.uploadFailed')))
    }
  }

  return {
    canvasDropActive,
    uploadInput,
    pendingUpload,
    uploadRules,
    handleCanvasDragOver,
    handleCanvasDragLeave,
    handleCanvasDrop,
    chooseUpload,
    handlePaneUpload,
  }
}
