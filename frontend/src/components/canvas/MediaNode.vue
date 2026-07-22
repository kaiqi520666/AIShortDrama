<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { AudioWaveform, FileText, GripVertical, Image as ImageIcon, MoveDiagonal2, Music2, Video } from 'lucide-vue-next'
import { imageAspectRatios } from '../../config/imageSettings'
import { useCanvasStore } from '../../stores/canvas'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

const icons = { text: FileText, image: ImageIcon, video: Video, audio: Music2 }
const icon = computed(() => icons[props.type])
const textMode = computed(() => props.type === 'text' ? (props.data.textMode ?? (props.data.content ? 'manual' : null)) : null)
const acceptsInput = computed(() => props.type === 'text' ? textMode.value === 'task' : props.data.assetSource !== 'upload')
const mediaWidth = computed(() => {
  if (!['image', 'video'].includes(props.type)) return 0
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
  if (['image', 'video'].includes(props.type)) return { aspectRatio: (props.data.aspectRatio === 'adaptive' ? '16:9' : props.data.aspectRatio || '16:9').replace(':', ' / ') }
  return {}
})
const store = useCanvasStore()
const uploadNotice = ref('')
const imageRetry = ref(0)
const imageSrc = computed(() => {
  if (!props.data.asset || !imageRetry.value) return props.data.asset
  const separator = props.data.asset.includes('?') ? '&' : '?'
  return `${props.data.asset}${separator}retry=${imageRetry.value}`
})
const { updateNodeData, viewport } = useVueFlow()
let resizeState = null
let imageRetryTimer = null

function retryImage() {
  if (imageRetry.value >= 5 || imageRetryTimer) return
  imageRetryTimer = window.setTimeout(() => {
    imageRetryTimer = null
    imageRetry.value += 1
  }, 1000)
}

function resetImageRetry() {
  if (imageRetryTimer) window.clearTimeout(imageRetryTimer)
  imageRetryTimer = null
  imageRetry.value = 0
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
  const [aspectWidth, aspectHeight] = (props.data.aspectRatio || '16:9').split(':').map(Number)
  resizeState = mediaWidth.value
    ? { kind: 'media', x: event.clientX, width: props.data.displayWidth || mediaWidth.value, minWidth: aspectWidth / aspectHeight < 0.5 ? 96 : 180 }
    : { kind: 'free', x: event.clientX, y: event.clientY, width: props.data.width || (audio ? 360 : 350), height: props.data.height || (audio ? 170 : 220), minWidth: 260, minHeight: audio ? 120 : 160 }
  window.addEventListener('pointermove', resizeNode)
  window.addEventListener('pointerup', stopResize)
}

watch(() => props.data.asset, resetImageRetry)
onBeforeUnmount(() => {
  stopResize()
  resetImageRetry()
})
</script>

<template>
  <div class="media-node" :class="[`media-node--${type}`, { selected }]" :style="nodeStyle">
    <label class="node-title">
      <component :is="icon" :size="14" />
      <input
        class="node-title-input nodrag nopan"
        :value="data.title"
        aria-label="节点标题"
        @input="updateNodeData(id, { title: $event.target.value })"
        @keydown.stop
      />
    </label>
    <Handle v-if="acceptsInput" id="target" type="target" :position="Position.Left" />

    <div class="node-body" :style="bodyStyle">
      <div v-if="data.status === 'generating'" class="generating-state">
        <span></span>
        <p>生成中 {{ data.generationProgress || 0 }}%</p>
      </div>

      <div v-else-if="data.status === 'failed'" class="generation-failed-state">
        <p>{{ data.generationError || '生成失败' }}</p>
      </div>

      <div v-else-if="type === 'text' && !textMode" class="text-mode-chooser">
        <p>选择文本节点用途</p>
        <button class="nodrag nopan" @pointerdown.stop @click.stop="store.setTextMode(id, 'manual')"><FileText :size="18" /><span><strong>自己编写内容</strong><small>记录任意文本内容</small></span></button>
        <button class="nodrag nopan" @pointerdown.stop @click.stop="store.setTextMode(id, 'imageReverse')"><ImageIcon :size="18" /><span><strong>反推图片提示词</strong><small>创建图片上传与 AI 文本任务</small></span></button>
        <button class="nodrag nopan" @pointerdown.stop @click.stop="store.setTextMode(id, 'videoReverse')"><Video :size="18" /><span><strong>反推视频提示词</strong><small>创建视频上传与 AI 文本任务</small></span></button>
      </div>

      <textarea
        v-else-if="type === 'text'"
        class="text-node-editor nodrag nopan nowheel"
        :value="data.content"
        :placeholder="textMode === 'task' ? '等待生成…' : '输入内容…'"
        aria-label="文本节点内容"
        @input="updateNodeData(id, { content: $event.target.value, status: 'ready' })"
        @keydown.stop
      ></textarea>

      <template v-else-if="data.asset && type === 'image'">
        <img class="node-image" :src="imageSrc" :alt="data.title" @error="retryImage" />
        <span v-if="data.assetSource !== 'upload'" class="asset-badge">AI</span>
      </template>

      <video v-else-if="data.asset && type === 'video'" class="node-video nodrag nopan nowheel" :src="data.asset" :poster="data.poster" controls playsinline preload="metadata"></video>

      <div v-else-if="['image', 'video'].includes(type) && data.assetSource === 'upload'" class="media-upload-state">
        <button class="nodrag nopan" @pointerdown.stop @click.stop="uploadNotice = `${type === 'video' ? '视频' : '图片'}上传暂未接入`"><component :is="icon" :size="32" stroke-width="1.35" /><span>上传{{ type === 'video' ? '视频' : '图片' }}</span></button>
        <p v-if="uploadNotice">{{ uploadNotice }}</p>
      </div>

      <div v-else-if="type === 'audio' && data.status === 'ready'" class="audio-preview">
        <AudioWaveform :size="60" />
        <span>00:00</span>
      </div>

      <div v-else class="empty-preview">
        <component :is="icon" :size="42" stroke-width="1.35" />
      </div>

      <span v-if="type === 'text' && textMode" class="text-drag-handle" title="拖动节点"><GripVertical :size="16" /></span>
      <button v-if="type === 'text' && textMode" class="text-resize-handle nodrag nopan" title="调整尺寸" @pointerdown.stop.prevent="startResize">
        <MoveDiagonal2 :size="15" />
      </button>
      <button v-if="selected && ['image', 'video', 'audio'].includes(type)" class="media-resize-handle nodrag nopan" title="调整显示尺寸" @pointerdown.stop.prevent="startResize">
        <MoveDiagonal2 :size="15" />
      </button>
    </div>

    <Handle v-if="type !== 'text' || textMode" id="source" type="source" :position="Position.Right" />
  </div>
</template>
