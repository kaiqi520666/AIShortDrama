<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { AudioWaveform, FileText, Image as ImageIcon, MoveDiagonal2, Music2, Video } from 'lucide-vue-next'
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
const nodeStyle = computed(() => {
  if (props.type === 'text') return { width: `${props.data.width || 350}px` }
  if (props.type === 'image') {
    const ratio = imageAspectRatios.find((item) => item.value === (props.data.aspectRatio || '16:9'))
    return { width: `${Math.round(Number.parseInt(ratio.sizes['1K']) * 380 / 1536)}px` }
  }
  return {}
})
const bodyStyle = computed(() => {
  if (props.type === 'text') return { height: `${props.data.height || 220}px` }
  if (props.type === 'image') return { aspectRatio: (props.data.aspectRatio || '16:9').replace(':', ' / ') }
  return {}
})
const store = useCanvasStore()
const uploadNotice = ref('')
const { updateNodeData, viewport } = useVueFlow()
let resizeState = null

function resizeNode(event) {
  const zoom = viewport.value.zoom
  updateNodeData(props.id, {
    width: Math.max(260, Math.round(resizeState.width + (event.clientX - resizeState.x) / zoom)),
    height: Math.max(160, Math.round(resizeState.height + (event.clientY - resizeState.y) / zoom)),
  })
}

function stopResize() {
  window.removeEventListener('pointermove', resizeNode)
  window.removeEventListener('pointerup', stopResize)
  resizeState = null
}

function startResize(event) {
  resizeState = { x: event.clientX, y: event.clientY, width: props.data.width || 350, height: props.data.height || 220 }
  window.addEventListener('pointermove', resizeNode)
  window.addEventListener('pointerup', stopResize)
}

onBeforeUnmount(stopResize)
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
    <Handle v-if="type !== 'text' || textMode === 'task'" id="target" type="target" :position="Position.Left" />

    <div class="node-body" :style="bodyStyle">
      <div v-if="data.status === 'generating'" class="generating-state">
        <span></span>
        <p>正在生成…</p>
      </div>

      <div v-else-if="type === 'text' && !textMode" class="text-mode-chooser">
        <p>选择文本节点用途</p>
        <button class="nodrag nopan" @pointerdown.stop @click.stop="store.setTextMode(id, 'manual')"><FileText :size="18" /><span><strong>自己编写内容</strong><small>记录任意文本内容</small></span></button>
        <button class="nodrag nopan" @pointerdown.stop @click.stop="store.setTextMode(id, 'reverse')"><ImageIcon :size="18" /><span><strong>反推图片提示词</strong><small>创建图片与 AI 文本任务</small></span></button>
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
        <img class="node-image" :src="data.asset" :alt="data.title" />
        <span class="asset-badge">AI</span>
      </template>

      <div v-else-if="type === 'image'" class="image-upload-state nodrag nopan">
        <button @click="uploadNotice = '图片上传暂未接入'"><ImageIcon :size="32" stroke-width="1.35" /><span>上传图片</span></button>
        <p v-if="uploadNotice">{{ uploadNotice }}</p>
      </div>

      <div v-else-if="type === 'audio' && data.status === 'ready'" class="audio-preview">
        <AudioWaveform :size="60" />
        <span>00:00</span>
      </div>

      <div v-else class="empty-preview">
        <component :is="icon" :size="42" stroke-width="1.35" />
      </div>

      <button v-if="type === 'text' && textMode" class="text-resize-handle nodrag nopan" title="调整尺寸" @pointerdown.stop.prevent="startResize">
        <MoveDiagonal2 :size="15" />
      </button>
    </div>

    <Handle v-if="type !== 'text' || textMode" id="source" type="source" :position="Position.Right" />
  </div>
</template>
