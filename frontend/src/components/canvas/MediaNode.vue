<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { AudioWaveform, FileText, GripVertical, Image as ImageIcon, MoveDiagonal2, Music2, Upload, Video } from 'lucide-vue-next'
import { uploadMedia } from '../../api/uploads'
import { imageAspectRatios } from '../../config/imageSettings'
import { startGenerationPolling } from '../../services/generationPolling'
import { useCanvasStore } from '../../stores/canvas'
import AppButton from '../ui/AppButton.vue'
import AppInput from '../ui/AppInput.vue'
import AppTextarea from '../ui/AppTextarea.vue'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

const icons = { text: FileText, image: ImageIcon, video: Video, audio: Music2 }
const icon = computed(() => icons[props.type])
const textMode = computed(() => props.type === 'text' ? (props.data.textMode ?? (props.data.content ? 'manual' : null)) : null)
const acceptsInput = computed(() => props.type !== 'audio' && (props.type === 'text' ? textMode.value === 'task' : !props.data.assetSource))
const sourceAspectRatio = computed(() => props.data.assetSource && props.data.sourceAspectRatio > 0 ? props.data.sourceAspectRatio : null)
const displayAspectRatio = computed(() => {
  if (sourceAspectRatio.value) return sourceAspectRatio.value
  const value = props.data.aspectRatio === 'adaptive' ? '16:9' : props.data.aspectRatio || '16:9'
  const [width, height] = value.split(':').map(Number)
  return width / height
})
const mediaWidth = computed(() => {
  if (!['image', 'video'].includes(props.type)) return 0
  if (sourceAspectRatio.value) {
    const baseWidth = props.type === 'video' ? 390 : 380
    const width = Math.sqrt(baseWidth * (baseWidth / (16 / 9)) * sourceAspectRatio.value)
    return Math.min(570, Math.max(96, Math.round(width)))
  }
  const aspectRatio = props.data.aspectRatio === 'adaptive' ? '16:9' : props.data.aspectRatio || '16:9'
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
const uploadNotice = ref('')
const fileInput = ref(null)
const audioElement = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadRules = {
  image: { types: ['image/jpeg', 'image/png', 'image/webp'], maxSize: 20 * 1024 * 1024 },
  video: { types: ['video/mp4', 'video/quicktime', 'video/webm'], maxSize: 500 * 1024 * 1024 },
}
const { updateNodeData, viewport } = useVueFlow()
let resizeState = null

function readMediaMetadata(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const media = props.type === 'image' ? new Image() : document.createElement('video')
    const cleanup = () => URL.revokeObjectURL(url)
    media.onload = media.onloadedmetadata = () => {
      const width = media.naturalWidth || media.videoWidth
      const height = media.naturalHeight || media.videoHeight
      cleanup()
      width && height ? resolve({ width, height, duration: media.duration || null }) : reject(new Error('无法读取媒体尺寸'))
    }
    media.onerror = () => {
      cleanup()
      reject(new Error('无法读取媒体文件'))
    }
    media.preload = 'metadata'
    media.src = url
  })
}

async function handleUpload(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const rule = uploadRules[props.type]
  if (!rule.types.includes(file.type)) {
    uploadNotice.value = `不支持的${props.type === 'video' ? '视频' : '图片'}格式`
    return
  }
  if (file.size > rule.maxSize) {
    uploadNotice.value = `文件不能超过 ${rule.maxSize / 1024 / 1024}MB`
    return
  }
  const replacementWidth = props.data.asset ? props.data.displayWidth || mediaWidth.value : null
  uploading.value = true
  uploadProgress.value = 0
  uploadNotice.value = ''
  try {
    const metadata = await readMediaMetadata(file)
    const result = await uploadMedia(props.type, file, {
      workspaceId: store.workspaceId,
      nodeId: props.id,
      ...metadata,
    }, (progress) => { uploadProgress.value = progress })
    if (result.code !== 0) throw new Error(result.message)
    updateNodeData(props.id, {
      asset: result.data.url,
      assetId: result.data.id,
      status: 'ready',
      sourceWidth: metadata.width,
      sourceHeight: metadata.height,
      sourceAspectRatio: metadata.width / metadata.height,
      ...(replacementWidth ? { displayWidth: replacementWidth } : {}),
      ...(metadata.duration ? { sourceDuration: metadata.duration } : {}),
    })
  } catch (error) {
    uploadNotice.value = error.response?.data?.message || error.message || '上传失败'
  } finally {
    uploading.value = false
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
watch(() => props.data.asset, (asset) => {
  if (props.type === 'audio' && asset) nextTick(() => audioElement.value?.load())
})
onBeforeUnmount(() => {
  stopResize()
})
</script>

<template>
  <div class="media-node" :class="[`media-node--${type}`, { selected }]" :style="nodeStyle">
    <label class="node-title">
      <component :is="icon" :size="14" />
      <AppInput
        class="node-title-input nodrag nopan"
        :model-value="data.title"
        aria-label="节点标题"
        @input="updateNodeData(id, { title: $event.target.value })"
        @keydown.stop
      />
    </label>
    <Handle v-if="acceptsInput" id="target" type="target" :position="Position.Left" />

    <div class="node-body" :style="bodyStyle">
      <input v-if="['upload', 'clipboard'].includes(data.assetSource)" ref="fileInput" type="file" :accept="type === 'video' ? 'video/mp4,video/quicktime,video/webm' : 'image/jpeg,image/png,image/webp'" hidden @change="handleUpload" />

      <div v-if="['generating', 'uploading'].includes(data.status) && type !== 'text'" class="generating-state">
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
        <AppButton class="nodrag nopan" @pointerdown.stop @click.stop="store.setTextMode(id, 'videoReverse')"><Video :size="18" /><span><strong>反推视频提示词</strong><small>创建视频上传与 AI 文本任务</small></span></AppButton>
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
        <img class="node-image" :src="data.asset" :alt="data.title" referrerpolicy="no-referrer" />
      </template>

      <video v-else-if="data.asset && type === 'video'" class="node-video nodrag nopan nowheel" :src="data.asset" :poster="data.poster" controls playsinline preload="metadata"></video>

      <div v-else-if="['image', 'video'].includes(type) && data.assetSource === 'upload'" class="media-upload-state">
        <AppButton class="nodrag nopan" :disabled="uploading" @pointerdown.stop @click.stop="fileInput?.click()"><component :is="icon" :size="32" stroke-width="1.35" /><span>{{ uploading ? `上传中 ${uploadProgress}%` : `上传${type === 'video' ? '视频' : '图片'}` }}</span></AppButton>
        <p v-if="uploadNotice">{{ uploadNotice }}</p>
      </div>

      <div v-else-if="type === 'audio' && data.asset" class="audio-preview">
        <AudioWaveform :size="60" />
        <audio ref="audioElement" class="node-audio nodrag nopan nowheel" :src="data.asset" controls preload="metadata"></audio>
      </div>

      <div v-else-if="type === 'audio' && data.status === 'ready'" class="audio-preview">
        <AudioWaveform :size="60" />
        <span>00:00</span>
      </div>

      <div v-else class="empty-preview">
        <component :is="icon" :size="42" stroke-width="1.35" />
      </div>

      <span v-if="type === 'text' && textMode" class="text-drag-handle" title="拖动节点"><GripVertical :size="16" /></span>
      <AppButton v-if="type === 'text' && textMode" class="text-resize-handle nodrag nopan" icon-only title="调整尺寸" @pointerdown.stop.prevent="startResize">
        <MoveDiagonal2 :size="15" />
      </AppButton>
      <AppButton v-if="type === 'image' && data.asset && ['upload', 'clipboard'].includes(data.assetSource)" class="media-reupload-button nodrag nopan" icon-only :disabled="uploading" title="重新上传图片" @pointerdown.stop @click.stop="fileInput?.click()">
        <Upload :size="15" />
      </AppButton>
      <AppButton v-if="selected && ['image', 'video', 'audio'].includes(type)" class="media-resize-handle nodrag nopan" icon-only title="调整显示尺寸" @pointerdown.stop.prevent="startResize">
        <MoveDiagonal2 :size="15" />
      </AppButton>
    </div>

    <Handle v-if="type !== 'text' || textMode" id="source" type="source" :position="Position.Right" />
  </div>
</template>
