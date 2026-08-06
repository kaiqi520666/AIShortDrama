import { getCurrentInstance, onBeforeUnmount, onMounted } from 'vue'
import { uploadMedia } from '../api/uploads'
import { mediaUploadRules, readMediaMetadata } from '../utils/mediaFiles'

export function useCanvasClipboard({ store, nodes, project, updateNodeData, toast, eventTarget = globalThis.window }) {
  let pastePoint = null

  function pasteText(text, position) {
    const id = store.addNode('text', position)
    const node = nodes.value.find((item) => item.id === id)
    node.data = { ...node.data, textMode: 'manual', content: text, status: 'ready', pasted: true }
  }

  async function pasteImage(file, position) {
    const rule = mediaUploadRules.image
    if (!rule.types.includes(file.type)) return toast.warning('仅支持粘贴 JPG、PNG 或 WebP 图片')
    if (file.size > rule.maxSize) return toast.warning('粘贴图片不能超过 20MB')

    const id = store.addNode('image', position)
    const node = nodes.value.find((item) => item.id === id)
    node.data = { ...node.data, status: 'uploading', assetSource: 'clipboard', pasted: true }
    try {
      const metadata = await readMediaMetadata('image', file)
      const result = await uploadMedia('image', file, {
        workspaceId: store.workspaceId,
        nodeId: id,
        timeout: 60_000,
        ...metadata,
      })
      if (result.code !== 0) throw new Error(result.message)
      const sourceWidth = result.data.width || metadata.width
      const sourceHeight = result.data.height || metadata.height
      updateNodeData(id, {
        asset: result.data.url,
        assetId: result.data.id,
        status: 'ready',
        sourceWidth,
        sourceHeight,
        sourceAspectRatio: sourceWidth / sourceHeight,
      })
      toast.success('图片已粘贴到画布')
    } catch (error) {
      store.deleteNode(id)
      toast.error(error.code === 'ECONNABORTED' ? '图片上传超时，请重试' : error.response?.data?.message || error.message || '图片粘贴失败')
    }
  }

  async function pasteFromClipboard(position) {
    try {
      if (!navigator.clipboard?.read) {
        const text = (await navigator.clipboard.readText()).trim()
        return text ? pasteText(text, position) : toast.warning('剪贴板中没有可粘贴内容')
      }
      const items = await navigator.clipboard.read()
      for (const item of items) {
        const imageType = item.types.find((type) => type.startsWith('image/'))
        if (imageType) {
          const blob = await item.getType(imageType)
          return pasteImage(new File([blob], 'clipboard-image', { type: imageType }), position)
        }
      }
      const textItem = items.find((item) => item.types.includes('text/plain'))
      const text = textItem ? (await (await textItem.getType('text/plain')).text()).trim() : ''
      return text ? pasteText(text, position) : toast.warning('剪贴板中没有可粘贴内容')
    } catch {
      toast.error('无法读取剪贴板，请允许浏览器访问剪贴板')
    }
  }

  function trackPastePoint(event) {
    if (event.target.closest('.creative-flow') && !event.target.closest('.vue-flow__node, .generation-panel, .node-create-menu')) {
      pastePoint = { x: event.clientX, y: event.clientY }
    }
  }

  function handlePaste(event) {
    const editable = event.target instanceof Element && event.target.closest('input, textarea, [contenteditable]:not([contenteditable="false"])')
    if (editable || !pastePoint) return
    const imageItem = Array.from(event.clipboardData?.items || []).find((item) => item.kind === 'file' && item.type.startsWith('image/'))
    const text = event.clipboardData?.getData('text/plain')?.trim()
    if (!imageItem && !text) return

    event.preventDefault()
    const position = project(pastePoint)
    const imageFile = imageItem?.getAsFile()
    if (imageItem && !imageFile) return toast.error('无法读取剪贴板图片')
    if (imageFile) pasteImage(imageFile, position)
    else pasteText(text, position)
  }

  if (getCurrentInstance()) {
    onMounted(() => eventTarget?.addEventListener('paste', handlePaste))
    onBeforeUnmount(() => eventTarget?.removeEventListener('paste', handlePaste))
  }

  return { pasteFromClipboard, pasteText, pasteImage, trackPastePoint, handlePaste }
}
