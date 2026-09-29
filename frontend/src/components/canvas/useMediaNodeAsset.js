import { i18n } from '../../i18n/index'
import { computed, ref } from 'vue'
import { Clapperboard, FileText, Images, Image as ImageIcon, Music2, Shirt, UserRound, Video } from 'lucide-vue-next'
import { registerAssetPrivateAvatar } from '../../api/assets'
import { uploadMedia } from '../../api/uploads'
import { getApiErrorMessage } from '../../utils/apiError'
import { downloadUrl } from '../../utils/download'
import { mediaUploadRules, readMediaMetadata, validateMediaFile } from '../../utils/mediaFiles'

const { t } = i18n.global

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
    if (inputRole.value === 'role') return { label: t('canvas.character'), icon: UserRound }
    if (inputRole.value === 'scene') return { label: t('canvas.scene'), icon: Images }
    return {
      model: { label: t('canvas.model'), icon: UserRound },
      garment: { label: t('canvas.garment'), icon: Shirt },
    }[resourceType.value] || { label: t('canvas.media'), icon: Images }
  })
  const libraryToolbarLabel = computed(() => (
    inputRole.value
      ? t('canvas.typedLibrary', { p0: libraryCopy.value.label })
      : resourceType.value === 'asset' ? t('canvas.assetLibrary') : t('canvas.typedLibrary', { p0: libraryCopy.value.label })
  ))
  const storyboardAsset = computed(() => props.data.storyboardAsset || {})
  const storyboardRegistrationLabel = computed(() => {
    if (!props.data.assetId) return t('canvas.missingAssetRecord')
    return ({
      active: t('canvas.seedanceCharacterReady'),
      processing: t('canvas.refreshSeedanceReview'),
      failed: t('canvas.retrySeedanceRegistration'),
    }[storyboardAsset.value.status] || t('canvas.registerSeedanceCharacter'))
  })
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
        ...(props.type === 'image' ? { storyboardAsset: null } : {}),
      })
    } catch (error) {
      uploadNotice.value = getApiErrorMessage(error, t('canvas.uploadFailed'))
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
      ...(props.type === 'image' ? { storyboardAsset: item.metadata?.seedance || null } : {}),
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
      toast.error(error.message || t('canvas.imageDownloadFailed'))
    } finally {
      downloading.value = false
    }
  }

  function openImagePreview() {
    store.selectNodes([props.id])
    previewOpen.value = true
  }

  function createStoryboardVideo() {
    if (!store.addStoryboardVideoNode(props.id)) toast.error(t('canvas.generateStoryboardFirst'))
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
      if (seedance?.status === 'active') toast.success(t('canvas.characterSeedanceReady'))
      else toast.info(t('canvas.characterReviewing'))
    } catch (error) {
      const seedance = error.response?.data?.data?.metadata?.seedance
      if (seedance) updateNodeData(props.id, { storyboardAsset: seedance })
      toast.error(getApiErrorMessage(error, t('canvas.characterAssetRegistrationFailed')))
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
