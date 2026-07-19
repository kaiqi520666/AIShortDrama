<script setup>
import { computed } from 'vue'
import { Handle, Position, useVueFlow } from '@vue-flow/core'
import { AudioWaveform, FileText, Image as ImageIcon, Music2, Video } from 'lucide-vue-next'

const props = defineProps({
  id: { type: String, required: true },
  type: { type: String, required: true },
  data: { type: Object, required: true },
  selected: Boolean,
})

const icons = { text: FileText, image: ImageIcon, video: Video, audio: Music2 }
const icon = computed(() => icons[props.type])
const nodeStyle = computed(() => {
  if (props.type !== 'image') return {}
  const [width, height] = (props.data.aspectRatio || '16:9').split(':').map(Number)
  return { width: `${Math.round(Math.sqrt(81225 * width / height))}px` }
})
const bodyStyle = computed(() => {
  if (props.type !== 'image') return {}
  const ratio = props.data.aspectRatio || '16:9'
  return { aspectRatio: ratio.replace(':', ' / ') }
})
const { updateNodeData } = useVueFlow()

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
    <Handle id="target" type="target" :position="Position.Left" />

    <div class="node-body" :style="bodyStyle">
      <div v-if="data.status === 'generating'" class="generating-state">
        <span></span>
        <p>正在生成…</p>
      </div>

      <template v-else-if="data.asset && type === 'image'">
        <img class="node-image" :src="data.asset" :alt="data.title" />
        <span class="asset-badge">AI</span>
      </template>

      <div v-else-if="type === 'text' && data.content" class="text-preview">
        <FileText :size="28" />
        <p>{{ data.content }}</p>
      </div>

      <div v-else-if="type === 'audio' && data.status === 'ready'" class="audio-preview">
        <AudioWaveform :size="60" />
        <span>00:00</span>
      </div>

      <div v-else class="empty-preview">
        <component :is="icon" :size="42" stroke-width="1.35" />
      </div>
    </div>

    <Handle id="source" type="source" :position="Position.Right" />
  </div>
</template>
