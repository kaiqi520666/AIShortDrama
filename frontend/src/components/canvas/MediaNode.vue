<script setup>
import { computed } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { AudioWaveform, BadgeCheck, Clapperboard, Download, Eye, FileText, GripVertical, Images, Image as ImageIcon, LoaderCircle, LockKeyhole, MoveDiagonal2, Music2, RefreshCw, Shirt, UserRound, Video } from 'lucide-vue-next'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { imageAspectRatios } from '../../config/imageSettings'
import { useCanvasStore } from '../../stores/canvas'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppAssetPickerModal from '../assets/AppAssetPickerModal.vue'
import AppButton from '../ui/AppButton.vue'
import AppInput from '../ui/AppInput.vue'
import AppMediaPreview from '../ui/AppMediaPreview.vue'
import AppTextarea from '../ui/AppTextarea.vue'
import AppTooltip from '../ui/AppTooltip.vue'
import { useMediaNodeAsset } from './useMediaNodeAsset'
import { useMediaNodeResize } from './useMediaNodeResize'
import { useNodeGenerationPolling } from './useNodeGenerationPolling'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

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
const { updateNodeData, viewport } = useVueFlow()
const toolbarStyle = computed(() => ({ '--toolbar-scale': 1 / viewport.value.zoom }))
const asset = useMediaNodeAsset({ props, store, toast, updateNodeData, mediaWidth })
const {
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
} = asset
const { startResize } = useMediaNodeResize({
  getId: () => props.id,
  getType: () => props.type,
  getData: () => props.data,
  getMediaWidth: () => mediaWidth.value,
  getDisplayAspectRatio: () => displayAspectRatio.value,
  getZoom: () => viewport.value.zoom,
  updateNodeData,
})
const { resume: resumeGenerationPolling } = useNodeGenerationPolling({
  getId: () => props.id,
  getData: () => props.data,
  getWorkspaceId: () => store.workspaceId,
  updateNodeData,
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
        <template v-if="data.generationPollingPaused">
          <p>{{ data.generationError || '状态同步中断' }}</p>
          <AppButton class="nodrag nopan" size="sm" @click.stop="resumeGenerationPolling"><RefreshCw :size="14" />继续同步</AppButton>
        </template>
        <template v-else>
          <span></span>
          <p>{{ data.status === 'uploading' ? '上传中' : `生成中 ${data.generationProgress || 0}%` }}</p>
        </template>
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

    <Handle v-if="type !== 'text' || textMode" id="source" type="source" :position="Position.Right" :connectable-start="!data.workflowId" />

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
