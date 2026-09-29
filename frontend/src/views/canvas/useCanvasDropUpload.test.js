import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { i18n } from '../../i18n'

import { ref } from 'vue'
import { uploadMedia } from '../../api/uploads'
import { readMediaMetadata } from '../../utils/mediaFiles'
import { uploadRules, useCanvasDropUpload, validateUploadFile } from './useCanvasDropUpload'

beforeEach(() => { i18n.global.locale.value = 'zh-CN' })
afterEach(() => { i18n.global.locale.value = 'id' })

vi.mock('../../api/uploads', () => ({ uploadMedia: vi.fn() }))
vi.mock('../../utils/mediaFiles', async (importOriginal) => ({
  ...await importOriginal(),
  readMediaMetadata: vi.fn(),
}))

function createUploadSubject() {
  const nodes = ref([])
  const store = {
    workspaceId: 'workspace-1',
    addNode: vi.fn((type, position) => {
      const id = `${type}-1`
      nodes.value.push({ id, type, position, data: {} })
      return id
    }),
    addAssetNode: vi.fn(),
    deleteNode: vi.fn(),
  }
  const contextMenu = ref({ position: { x: 120, y: 80 } })
  const activeGroupId = ref('group-1')
  const updateNodeData = vi.fn()
  const toast = { error: vi.fn(), warning: vi.fn() }
  const subject = useCanvasDropUpload({
    store,
    nodes,
    contextMenu,
    activeGroupId,
    screenToFlowCoordinate: vi.fn((position) => position),
    updateNodeData,
    toast,
  })
  return { subject, store, nodes, updateNodeData, toast }
}

beforeEach(() => vi.clearAllMocks())

describe('canvas drop uploads', () => {
  it('accepts supported media within the configured limit', () => {
    expect(validateUploadFile('image', { type: 'image/png', size: 1024 })).toBe('')
  })

  it('rejects unsupported formats and oversized files', () => {
    expect(validateUploadFile('image', { type: 'image/gif', size: 1024 })).toContain('不支持的图片格式')
    expect(validateUploadFile('video', { type: 'video/mp4', size: uploadRules.video.maxSize + 1 })).toContain('文件不能超过')
    expect(validateUploadFile('document', { type: 'text/plain', size: 1 })).toBe('不支持的上传类型')
  })

  it('uploads media metadata and writes the ready asset state', async () => {
    const { subject, store, nodes, updateNodeData } = createUploadSubject()
    const file = { name: 'source.png', type: 'image/png', size: 1024 }
    readMediaMetadata.mockResolvedValue({ width: 640, height: 480 })
    uploadMedia.mockResolvedValue({
      code: 0,
      data: {
        id: 'asset-1',
        url: 'https://example.com/source.png',
        width: 800,
        height: 600,
        size: 2048,
      },
    })
    subject.pendingUpload.value = { type: 'image', position: { x: 120, y: 80 } }

    await subject.handlePaneUpload({ target: { files: [file], value: 'selected' } })

    expect(store.addNode).toHaveBeenCalledWith('image', { x: 120, y: 80 })
    expect(nodes.value[0].data).toMatchObject({ status: 'uploading', assetSource: 'upload', pasted: true })
    expect(uploadMedia).toHaveBeenCalledWith('image', file, {
      workspaceId: 'workspace-1',
      nodeId: 'image-1',
      timeout: 60_000,
      width: 640,
      height: 480,
    })
    expect(updateNodeData).toHaveBeenCalledWith('image-1', {
      asset: 'https://example.com/source.png',
      assetId: 'asset-1',
      status: 'ready',
      sourceWidth: 800,
      sourceHeight: 600,
      sourceAspectRatio: 4 / 3,
      sourceByteSize: 2048,
    })
  })

  it('deletes the temporary node and reports an upload failure', async () => {
    const { subject, store, updateNodeData, toast } = createUploadSubject()
    const file = { name: 'source.mp4', type: 'video/mp4', size: 1024 }
    readMediaMetadata.mockResolvedValue({ width: 1920, height: 1080, duration: 5 })
    uploadMedia.mockRejectedValue({ response: { status: 503, data: { message: '上传服务不可用', error_key: 'service_unavailable' } } })
    subject.pendingUpload.value = { type: 'video', position: { x: 20, y: 30 } }

    await subject.handlePaneUpload({ target: { files: [file], value: 'selected' } })

    expect(store.deleteNode).toHaveBeenCalledWith('video-1')
    expect(updateNodeData).not.toHaveBeenCalled()
    expect(toast.error).toHaveBeenCalledWith(i18n.global.t('errors.service_unavailable'))
  })
})
