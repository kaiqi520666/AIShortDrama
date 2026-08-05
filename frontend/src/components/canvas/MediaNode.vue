<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { AudioWaveform, BadgeCheck, Clapperboard, Download, Eye, FileText, GripVertical, Images, Image as ImageIcon, LoaderCircle, LockKeyhole, MoveDiagonal2, Music2, RefreshCw, Shirt, UserRound, Video } from 'lucide-vue-next'
import { registerAssetPrivateAvatar } from '../../api/assets'
import { uploadMedia } from '../../api/uploads'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { imageAspectRatios } from '../../config/imageSettings'
import { startGenerationPolling } from '../../services/generationPolling'
import { useCanvasStore } from '../../stores/canvas'
import { downloadUrl } from '../../utils/download'
import { buildOssImageUrl } from '../../utils/ossImage'
import { mediaUploadRules, readMediaMetadata, validateMediaFile } from '../../utils/mediaFiles'
import AppAssetPickerModal from '../assets/AppAssetPickerModal.vue'
import AppButton from '../ui/AppButton.vue'
import AppInput from '../ui/AppInput.vue'
import AppMediaPreview from '../ui/AppMediaPreview.vue'
import AppTextarea from '../ui/AppTextarea.vue'
import AppTooltip from '../ui/AppTooltip.vue'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

const icons = { text: FileText, image: ImageIcon, video: Video, audio: Music2 }
const icon = computed(() => props.type === 'image' && props.data.storyboardSourceId ? Clapperboard : icons[props.type])
const textMode = computed(() => props.type === 'text' ? (props.data.textMode ?? (props.data.content ? 'manual' : null)) : null)
const acceptsInput = computed(() => props.type === 'text' ? textMode.value === 'task' : !props.data.assetSource)
const sourceAspectRatio = computed(() => props.data.assetSource && props.data.sourceAspectRatio > 0 ? props.data.sourceAspectRatio : null)
const selectedAspectRatio = computed(() => props.data.aspectRatio === 'adaptive' ? '16:9' : props.data.aspectRatio || (props.type === 'image' ? '1:1' : '16:9'))
const displayAspectRatio = computed(() => {
  if (sourceAspectRatio.value) return sourceAspectRatio.value
  const [width, height] = selectedAspectRatio.value.split(':').map(Number)
  return width / height
})
const mediaWidth = computed(() => {
  if (!['image', 'video'].includes(props.type)) return 0
  if (sourceAspectRatio.value) {
    const baseWidth = props.type === 'video' ? 390 : 380
    const width = Math.sqrt(baseWidth * (baseWidth / (16 / 9)) * sourceAspectRatio.value)
    return Math.min(570, Math.max(96, Math.round(width)))
  }
  const aspectRatio = selectedAspectRatio.value
  const ratio = imageAspectRatios.find((item) => item.value === aspectRatio)
    || imageAspectRatios.find((item) => item.value === '16:9')
  const baseWidth = props.type === 'video' ? 390 : 380
  if (ratio.sizes?.['1K']) return Math.round(Number.parseInt(ratio.sizes['1K']) * baseWidth / 1536)
  const [width, height] = aspectRatio.split(':').map(Number)
  const aspect = width / height
  return aspect >= 1 ? Math.min(570, Math.round(baseWidth * aspect / (16 / 9))) : Math.max(96, Math.round(baseWidth * aspect / (9 / 16)))
})
const nodeStyle = computed(() => {
  if (props.type === 'text') return { width: `${props.data.width || 350}px` }
  if (props.type === 'audio') return { width: `${props.data.width || 360}px` }
  if (mediaWidth.value) return { width: `${props.data.displayWidth || mediaWidth.value}px` }
  return {}
})
const bodyStyle = computed(() => {
  if (props.type === 'text') return { height: `${props.data.height || (textMode.value ? 220 : 280)}px` }
  if (props.type === 'audio') return { height: `${props.data.height || 170}px` }
  if (['image', 'video'].includes(props.type)) return { aspectRatio: displayAspectRatio.value }
  return {}
})
const store = useCanvasStore()
const toast = useGlobalToast()
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
const libraryToolbarLabel = computed(() => inputRole.value ? `${libraryCopy.value.label}库` : resourceType.value === 'asset' ? '资产库' : `${libraryCopy.value.label}库`)
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
const { updateNodeData, viewport } = useVueFlow()
const toolbarStyle = computed(() => ({ '--toolbar-scale': 1 / viewport.value.zoom }))
let resizeState = null

async function handleUpload(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const validationError = validateMediaFile(props.type, file)
  if (validationError) return uploadNotice.value = validationError
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
    uploadNotice.value = error.response?.data?.message || error.message || '上传失败'
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
    const result = await registerAssetPrivateAvatar(props.data.assetId, props.data.storyboardCharacterReferences?.[0]?.groupId || null)
    const seedance = result.data?.metadata?.seedance
    if (seedance) updateNodeData(props.id, { storyboardAsset: seedance })
    if (result.code !== 0) throw new Error(result.message)
    if (seedance?.status === 'active') toast.success('分镜虚拟人像素材已可用于 Seedance')
    else toast.info('分镜素材审核中，请稍后点击刷新')
  } catch (error) {
    toast.error(error.response?.data?.message || error.message || '分镜素材注册失败')
  } finally {
    registeringStoryboard.value = false
  }
}

function resizeNode(event) {
  const zoom = viewport.value.zoom
  if (resizeState.kind === 'media') {
    updateNodeData(props.id, { displayWidth: Math.min(720, Math.max(resizeState.minWidth, Math.round(resizeState.width + (event.clientX - resizeState.x) / zoom))) })
    return
  }
  updateNodeData(props.id, {
    width: Math.max(resizeState.minWidth, Math.round(resizeState.width + (event.clientX - resizeState.x) / zoom)),
    height: Math.max(resizeState.minHeight, Math.round(resizeState.height + (event.clientY - resizeState.y) / zoom)),
  })
}

function stopResize() {
  window.removeEventListener('pointermove', resizeNode)
  window.removeEventListener('pointerup', stopResize)
  resizeState = null
}

function startResize(event) {
  const audio = props.type === 'audio'
  resizeState = mediaWidth.value
    ? { kind: 'media', x: event.clientX, width: props.data.displayWidth || mediaWidth.value, minWidth: displayAspectRatio.value < 0.5 ? 96 : 180 }
    : { kind: 'free', x: event.clientX, y: event.clientY, width: props.data.width || (audio ? 360 : 350), height: props.data.height || (audio ? 170 : 220), minWidth: 260, minHeight: audio ? 120 : 160 }
  window.addEventListener('pointermove', resizeNode)
  window.addEventListener('pointerup', stopResize)
}

watch(
  () => [props.data.generationTaskId, props.data.status],
  ([taskId, status]) => {
    if (taskId && status === 'generating') startGenerationPolling(taskId, props.id, updateNodeData)
  },
  { immediate: true },
)
onBeforeUnmount(() => {
  stopResize()
})
</script>

<template>
  <div class="media-node" :class="[`media-node--${type}`, { selected }]" :style="nodeStyle">
    <div v-if="selected && type === 'image' && data.asset" class="media-node-toolbar nodrag nopan" :style="toolbarStyle" @pointerdown.stop>
      <AppTooltip v-if="data.assetSource" :text="libraryToolbarLabel">
        <AppButton class="media-node-toolbar-button" icon-only :aria-label="libraryToolbarLabel" @click.stop="openAssetPicker"><component :is="libraryCopy.icon" :size="16" /></AppButton>
      </AppTooltip>
      <AppTooltip v-if="data.storyboardSourceId" text="创建视频节点">
        <AppButton class="media-node-toolbar-button" icon-only aria-label="创建视频节点" @click.stop="createStoryboardVideo"><Video :size="16" /></AppButton>
      </AppTooltip>
      <AppTooltip v-if="data.storyboardSourceId" :text="storyboardRegistrationLabel">
        <AppButton class="media-node-toolbar-button" icon-only :disabled="registeringStoryboard || !data.assetId" :aria-label="storyboardRegistrationLabel" @click.stop="registerStoryboardAsset">
          <LoaderCircle v-if="registeringStoryboard" class="media-action-spinner" :size="16" />
          <BadgeCheck v-else-if="storyboardAsset.status === 'active'" :size="16" />
          <RefreshCw v-else-if="storyboardAsset.status === 'processing'" :size="16" />
          <UserRound v-else :size="16" />
        </AppButton>
      </AppTooltip>
      <AppTooltip text="预览原图">
        <AppButton class="media-node-toolbar-button" icon-only aria-label="预览原图" @click.stop="openImagePreview"><Eye :size="16" /></AppButton>
      </AppTooltip>
      <AppTooltip text="下载原图">
        <AppButton class="media-node-toolbar-button" icon-only :disabled="downloading" aria-label="下载原图" @click.stop="downloadImage">
          <LoaderCircle v-if="downloading" class="media-action-spinner" :size="16" /><Download v-else :size="16" />
        </AppButton>
      </AppTooltip>
    </div>
    <label class="node-title">
      <component :is="icon" :size="14" />
      <AppInput
        class="node-title-input nodrag nopan"
        :model-value="data.title"
        aria-label="节点标题"
        @input="updateNodeData(id, { title: $event.target.value })"
        @keydown.stop
      />
      <span v-if="imageResolution" class="node-resolution">{{ imageResolution }}</span>
    </label>
    <Handle v-if="acceptsInput" id="target" type="target" :position="Position.Left" />

    <div class="node-body" :style="bodyStyle">
      <input v-if="['upload', 'clipboard'].includes(data.assetSource)" ref="fileInput" type="file" :accept="uploadAccept" hidden @change="handleUpload" />

      <div v-if="data.segmentLocked" class="generation-locked-state">
        <LockKeyhole :size="28" />
        <p>等待上一段确认</p>
      </div>

      <div v-else-if="['generating', 'uploading'].includes(data.status) && type !== 'text'" class="generating-state">
        <span></span>
        <p>{{ data.status === 'uploading' ? '上传中' : `生成中 ${data.generationProgress || 0}%` }}</p>
      </div>

      <div v-else-if="data.status === 'failed' && type !== 'text'" class="generation-failed-state">
        <p>{{ data.generationError || '生成失败' }}</p>
      </div>

      <div v-else-if="type === 'text' && !textMode" class="text-mode-chooser">
        <p>选择文本节点用途</p>
        <AppButton class="nodrag nopan" @pointerdown.stop @click.stop="store.setTextMode(id, 'manual')"><FileText :size="18" /><span><strong>自己编写内容</strong><small>记录任意文本内容</small></span></AppButton>
        <AppButton class="nodrag nopan" @pointerdown.stop @click.stop="store.setTextMode(id, 'imageReverse')"><ImageIcon :size="18" /><span><strong>反推图片提示词</strong><small>创建图片上传与 AI 文本任务</small></span></AppButton>
      </div>

      <AppTextarea
        v-else-if="type === 'text'"
        class="text-node-editor nodrag nopan nowheel"
        :model-value="data.content"
        :placeholder="textMode === 'task' ? (data.status === 'generating' ? '正在生成…' : '等待生成…') : '输入内容…'"
        :readonly="textMode === 'task' && data.status === 'generating'"
        aria-label="文本节点内容"
        @input="updateNodeData(id, { content: $event.target.value, status: 'ready' })"
        @keydown.stop
      />

      <template v-else-if="data.asset && type === 'image'">
        <img class="node-image" :src="buildOssImageUrl(data.asset)" :alt="data.title" title="双击预览原图" draggable="false" referrerpolicy="no-referrer" @load="captureImageDimensions" @dblclick.stop="openImagePreview" />
      </template>

      <video v-else-if="data.assetId && type === 'video'" class="node-video nodrag nopan nowheel" :src="`/api/assets/${data.assetId}/content`" :poster="data.poster || data.lastFrameUrl" controls playsinline preload="none"></video>

      <div v-else-if="['image', 'video'].includes(type) && data.assetSource === 'upload'" class="media-upload-state">
        <div class="media-upload-actions">
          <AppButton v-if="resourceType === 'asset'" class="nodrag nopan" :disabled="uploading" @pointerdown.stop @click.stop="fileInput?.click()"><component :is="icon" :size="28" stroke-width="1.35" /><span>{{ uploading ? `上传中 ${uploadProgress}%` : `上传${type === 'video' ? '视频' : '图片'}` }}</span></AppButton>
          <AppButton v-if="type === 'image'" class="nodrag nopan" @pointerdown.stop @click.stop="openAssetPicker"><component :is="libraryCopy.icon" :size="28" stroke-width="1.35" /><span>选择{{ libraryCopy.label }}</span></AppButton>
        </div>
        <p v-if="uploadNotice">{{ uploadNotice }}</p>
      </div>

      <div v-else-if="type === 'audio' && data.assetId" class="audio-preview">
        <AudioWaveform :size="60" />
        <audio class="node-audio nodrag nopan nowheel" :src="`/api/assets/${data.assetId}/content`" controls preload="metadata"></audio>
      </div>

      <div v-else-if="type === 'audio' && data.status === 'ready'" class="audio-preview">
        <AudioWaveform :size="60" />
        <span>00:00</span>
      </div>

      <div v-else class="empty-preview">
        <component :is="icon" :size="42" stroke-width="1.35" />
      </div>

      <span v-if="type === 'video' || (type === 'text' && textMode)" class="node-drag-handle" title="拖动节点"><GripVertical :size="16" /></span>
      <AppButton v-if="type === 'text' && textMode" class="text-resize-handle nodrag nopan" icon-only title="调整尺寸" @pointerdown.stop.prevent="startResize">
        <MoveDiagonal2 :size="15" />
      </AppButton>
      <AppButton v-if="selected && ['image', 'video', 'audio'].includes(type)" class="media-resize-handle nodrag nopan" icon-only title="调整显示尺寸" @pointerdown.stop.prevent="startResize">
        <MoveDiagonal2 :size="15" />
      </AppButton>
    </div>

    <Handle v-if="type !== 'text' || textMode" id="source" type="source" :position="Position.Right" />

    <AppAssetPickerModal
      v-if="assetPickerOpen"
      :resource-type="resourceType"
      :include-asset-library="resourceType === 'character'"
      :input-role="inputRole"
      media-type="image"
      :workspace-id="store.workspaceId"
      :node-id="id"
      :selected-url="data.asset"
      :extra-item="pendingCharacterAsset"
      @close="assetPickerOpen = false"
      @open-asset-library="openCharacterAssetPicker"
      @select="selectAsset"
    />
    <AppAssetPickerModal
      v-if="characterAssetPickerOpen"
      resource-type="asset"
      media-type="image"
      :workspace-id="store.workspaceId"
      :node-id="id"
      :selected-url="data.asset"
      @close="characterAssetPickerOpen = false"
      @select="selectCharacterAsset"
    />
    <AppMediaPreview v-if="previewOpen" :src="data.asset" :title="data.title" :downloading="downloading" @close="previewOpen = false" @download="downloadImage" />
  </div>
</template>
