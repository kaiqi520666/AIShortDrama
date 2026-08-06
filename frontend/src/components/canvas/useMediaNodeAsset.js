import { computed, ref } from 'vue'
import { Clapperboard, FileText, Images, Image as ImageIcon, Music2, Shirt, UserRound, Video } from 'lucide-vue-next'
import { registerAssetPrivateAvatar } from '../../api/assets'
import { uploadMedia } from '../../api/uploads'
import { getApiErrorMessage } from '../../utils/apiError'
import { downloadUrl } from '../../utils/download'
import { mediaUploadRules, readMediaMetadata, validateMediaFile } from '../../utils/mediaFiles'

const icons = { text: FileText, image: ImageIcon, video: Video, audio: Music2 }

export function useMediaNodeAsset({ props, store, toast, updateNodeData, mediaWidth }) {
  const uploadNotice = ref('')
  const fileInput = ref(null)
  const uploading = ref(false)
  const uploadProgress = ref(0)
  const assetPickerOpen = ref(false)
  const characterAssetPickerOpen = ref(false)
  const pendingCharacterAsset = ref(null)
  const previewOpen = ref(false)
  const downloading = ref(false)
  const registeringStoryboard = ref(false)

  const icon = computed(() => (
    props.type === 'image' && props.data.storyboardSourceId
      ? Clapperboard
      : icons[props.type]
  ))
  const resourceType = computed(() => props.data.resourceType || 'asset')
  const inputRole = computed(() => props.data.inputRole || (
    props.data.title === '角色节点' ? 'role' : props.data.title === '场景节点' ? 'scene' : ''
  ))
  const libraryCopy = computed(() => {
    if (inputRole.value === 'role') return { label: '角色', icon: UserRound }
    if (inputRole.value === 'scene') return { label: '场景', icon: Images }
    return {
      model: { label: '模特', icon: UserRound },
      garment: { label: '服饰', icon: Shirt },
    }[resourceType.value] || { label: '素材', icon: Images }
  })
  const libraryToolbarLabel = computed(() => (
    inputRole.value
      ? `${libraryCopy.value.label}库`
      : resourceType.value === 'asset' ? '资产库' : `${libraryCopy.value.label}库`
  ))
  const storyboardAsset = computed(() => props.data.storyboardAsset || {})
  const storyboardRegistrationLabel = computed(() => ({
    active: 'Seedance 虚拟人像素材已可用',
    processing: '刷新虚拟人像素材审核状态',
    failed: '重新注册虚拟人像素材',
  }[storyboardAsset.value.status] || '注册虚拟人像素材'))
  const imageResolution = computed(() => {
    if (props.type !== 'image') return ''
    const width = Number(props.data.sourceWidth)
    const height = Number(props.data.sourceHeight)
    return width > 0 && height > 0 ? `${width} × ${height} px` : ''
  })
  const uploadAccept = computed(() => mediaUploadRules[props.type]?.types.join(',') || '')

  async function handleUpload(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    const validationError = validateMediaFile(props.type, file)
    if (validationError) {
      uploadNotice.value = validationError
      return
    }
    const replacementWidth = props.data.asset ? props.data.displayWidth || mediaWidth.value : null
    uploading.value = true
    uploadProgress.value = 0
    uploadNotice.value = ''
    try {
      const metadata = await readMediaMetadata(props.type, file)
      const result = await uploadMedia(props.type, file, {
        workspaceId: store.workspaceId,
        nodeId: props.id,
        ...metadata,
      }, (progress) => { uploadProgress.value = progress })
      if (result.code !== 0) throw new Error(result.message)
      const sourceWidth = result.data.width || metadata.width
      const sourceHeight = result.data.height || metadata.height
      updateNodeData(props.id, {
        asset: result.data.url,
        assetId: result.data.id,
        status: 'ready',
        sourceWidth,
        sourceHeight,
        sourceAspectRatio: sourceWidth / sourceHeight,
        ...(replacementWidth ? { displayWidth: replacementWidth } : {}),
        ...(metadata.duration ? { sourceDuration: metadata.duration } : {}),
        sourceByteSize: result.data.size,
        ...(props.data.storyboardSourceId ? { storyboardAsset: null } : {}),
      })
    } catch (error) {
      uploadNotice.value = getApiErrorMessage(error, '上传失败')
    } finally {
      uploading.value = false
    }
  }

  function selectAsset(item) {
    const sourceWidth = item.width
    const sourceHeight = item.height
    updateNodeData(props.id, {
      asset: item.url,
      assetId: item.assetId || null,
      assetSource: 'library',
      status: 'ready',
      sourceWidth,
      sourceHeight,
      sourceAspectRatio: sourceWidth && sourceHeight ? sourceWidth / sourceHeight : null,
      sourceByteSize: item.byteSize || null,
      resourceId: item.id,
      ...(props.data.storyboardSourceId ? { storyboardAsset: null } : {}),
    })
    assetPickerOpen.value = false
    characterAssetPickerOpen.value = false
    pendingCharacterAsset.value = null
  }

  function openCharacterAssetPicker() {
    characterAssetPickerOpen.value = true
  }

  function selectCharacterAsset(item) {
    pendingCharacterAsset.value = { ...item, mediaType: item.mediaType || 'image', pickerKind: 'asset' }
    characterAssetPickerOpen.value = false
  }

  function openAssetPicker() {
    pendingCharacterAsset.value = null
    assetPickerOpen.value = true
  }

  function captureImageDimensions() {
    if (props.type !== 'image' || imageResolution.value || !/^https?:\/\//i.test(props.data.asset || '')) return
    const asset = props.data.asset
    const image = new Image()
    image.referrerPolicy = 'no-referrer'
    image.onload = () => {
      if (props.data.asset !== asset || imageResolution.value || !image.naturalWidth || !image.naturalHeight) return
      updateNodeData(props.id, {
        sourceWidth: image.naturalWidth,
        sourceHeight: image.naturalHeight,
        sourceAspectRatio: image.naturalWidth / image.naturalHeight,
      })
    }
    image.src = asset
  }

  async function downloadImage() {
    if (!props.data.asset || downloading.value) return
    downloading.value = true
    try {
      await downloadUrl(props.data.asset, props.data.title)
    } catch (error) {
      toast.error(error.message || '图片下载失败')
    } finally {
      downloading.value = false
    }
  }

  function openImagePreview() {
    store.selectNodes([props.id])
    previewOpen.value = true
  }

  function createStoryboardVideo() {
    if (!store.addStoryboardVideoNode(props.id)) toast.error('请先生成分镜图片和视频脚本')
  }

  async function registerStoryboardAsset() {
    if (!props.data.assetId || registeringStoryboard.value) return
    registeringStoryboard.value = true
    try {
      const result = await registerAssetPrivateAvatar(
        props.data.assetId,
        props.data.storyboardCharacterReferences?.[0]?.groupId || null,
      )
      const seedance = result.data?.metadata?.seedance
      if (seedance) updateNodeData(props.id, { storyboardAsset: seedance })
      if (result.code !== 0) throw new Error(result.message)
      if (seedance?.status === 'active') toast.success('分镜虚拟人像素材已可用于 Seedance')
      else toast.info('分镜素材审核中，请稍后点击刷新')
    } catch (error) {
      toast.error(getApiErrorMessage(error, '分镜素材注册失败'))
    } finally {
      registeringStoryboard.value = false
    }
  }

  return {
    icon,
    uploadNotice,
    fileInput,
    uploading,
    uploadProgress,
    assetPickerOpen,
    characterAssetPickerOpen,
    pendingCharacterAsset,
    previewOpen,
    downloading,
    registeringStoryboard,
    resourceType,
    inputRole,
    libraryCopy,
    libraryToolbarLabel,
    storyboardAsset,
    storyboardRegistrationLabel,
    imageResolution,
    uploadAccept,
    handleUpload,
    selectAsset,
    openCharacterAssetPicker,
    selectCharacterAsset,
    openAssetPicker,
    captureImageDimensions,
    downloadImage,
    openImagePreview,
    createStoryboardVideo,
    registerStoryboardAsset,
  }
}
