import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { i18n } from '../../i18n'

import { ref } from 'vue'
import { registerAssetPrivateAvatar } from '../../api/assets'
import { uploadMedia } from '../../api/uploads'
import { downloadUrl } from '../../utils/download'
import { readMediaMetadata } from '../../utils/mediaFiles'
import { useMediaNodeAsset } from './useMediaNodeAsset'

beforeEach(() => { i18n.global.locale.value = 'zh-CN' })
afterEach(() => { i18n.global.locale.value = 'id' })

vi.mock('../../api/assets', () => ({ registerAssetPrivateAvatar: vi.fn() }))
vi.mock('../../api/uploads', () => ({ uploadMedia: vi.fn() }))
vi.mock('../../utils/download', () => ({ downloadUrl: vi.fn() }))
vi.mock('../../utils/mediaFiles', async (importOriginal) => ({
  ...await importOriginal(),
  readMediaMetadata: vi.fn(),
}))

function createSubject() {
  const props = {
    id: 'image-1',
    type: 'image',
    data: { title: '商品图', asset: '', status: 'empty' },
  }
  const store = { workspaceId: 'workspace-1', selectNodes: vi.fn() }
  const updateNodeData = vi.fn()
  const toast = { error: vi.fn(), success: vi.fn(), info: vi.fn() }
  const subject = useMediaNodeAsset({
    props,
    store,
    toast,
    updateNodeData,
    mediaWidth: ref(380),
  })
  return { props, store, updateNodeData, toast, subject }
}

beforeEach(() => vi.clearAllMocks())

describe('useMediaNodeAsset', () => {
  it('uploads metadata and writes the ready asset fields', async () => {
    const { subject, updateNodeData } = createSubject()
    readMediaMetadata.mockResolvedValue({ width: 640, height: 480 })
    uploadMedia.mockResolvedValue({
      code: 0,
      data: { id: 'asset-1', url: 'https://cdn.test/image.png', width: 800, height: 600, size: 2048 },
    })

    await subject.handleUpload({
      target: { files: [{ type: 'image/png', size: 1024 }], value: 'selected' },
    })

    expect(uploadMedia).toHaveBeenCalledWith('image', expect.any(Object), {
      workspaceId: 'workspace-1',
      nodeId: 'image-1',
      width: 640,
      height: 480,
    }, expect.any(Function))
    expect(updateNodeData).toHaveBeenCalledWith('image-1', expect.objectContaining({
      asset: 'https://cdn.test/image.png',
      assetId: 'asset-1',
      sourceAspectRatio: 4 / 3,
      status: 'ready',
      storyboardAsset: null,
    }))
    expect(subject.uploading.value).toBe(false)
  })

  it('keeps a public error when upload fails', async () => {
    const { subject } = createSubject()
    readMediaMetadata.mockResolvedValue({ width: 640, height: 480 })
    uploadMedia.mockRejectedValue({ response: { status: 503, data: { message: '上传服务不可用', error_key: 'service_unavailable' } } })

    await subject.handleUpload({
      target: { files: [{ type: 'image/png', size: 1024 }], value: 'selected' },
    })

    expect(subject.uploadNotice.value).toBe(i18n.global.t('errors.service_unavailable'))
    expect(subject.uploading.value).toBe(false)
  })

  it('writes library assets and closes the picker', () => {
    const { subject, updateNodeData } = createSubject()
    subject.assetPickerOpen.value = true

    subject.selectAsset({
      id: 'library-1',
      assetId: 'asset-2',
      url: 'https://cdn.test/library.png',
      width: 100,
      height: 200,
      byteSize: 300,
      metadata: { seedance: { status: 'active', asset_url: 'asset://library-person' } },
    })

    expect(updateNodeData).toHaveBeenCalledWith('image-1', expect.objectContaining({
      assetSource: 'library',
      resourceId: 'library-1',
      sourceAspectRatio: 0.5,
      storyboardAsset: { status: 'active', asset_url: 'asset://library-person' },
    }))
    expect(subject.assetPickerOpen.value).toBe(false)
  })

  it('registers an ordinary image as a Seedance person asset', async () => {
    const { props, subject, updateNodeData, toast } = createSubject()
    props.data.assetId = 'asset-1'
    registerAssetPrivateAvatar.mockResolvedValue({
      code: 0,
      data: { metadata: { seedance: { status: 'active', asset_url: 'asset://person-1' } } },
    })

    await subject.registerStoryboardAsset()

    expect(registerAssetPrivateAvatar).toHaveBeenCalledWith('asset-1', null)
    expect(updateNodeData).toHaveBeenCalledWith('image-1', {
      storyboardAsset: { status: 'active', asset_url: 'asset://person-1' },
    })
    expect(toast.success).toHaveBeenCalledWith('人物素材已可用于 Seedance')
  })
})
