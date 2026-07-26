<script setup>
import { computed, onMounted, ref } from 'vue'
import { ImagePlus, LoaderCircle, Music2, Search, Video } from 'lucide-vue-next'
import { listAssets } from '../../api/assets'
import { listReferenceItems, uploadReferenceItem } from '../../api/referenceLibrary'
import { uploadMedia } from '../../api/uploads'
import { normalizeLibraryItem } from '../../config/assetLibrary'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { buildOssImageUrl } from '../../utils/ossImage'
import { mediaUploadRules, readMediaMetadata, validateMediaFile } from '../../utils/mediaFiles'
import AppButton from '../ui/AppButton.vue'
import AppInput from '../ui/AppInput.vue'
import AppModal from '../ui/AppModal.vue'
import EmptyState from '../ui/EmptyState.vue'

const props = defineProps({
  resourceType: { type: String, default: 'asset', validator: (value) => ['asset', 'model', 'character'].includes(value) },
  mediaType: { type: String, default: 'image' },
  workspaceId: { type: String, default: '' },
  nodeId: { type: String, default: '' },
  selectedUrl: { type: String, default: '' },
})
const emit = defineEmits(['close', 'select'])
const toast = useGlobalToast()
const query = ref('')
const items = ref([])
const loading = ref(true)
const uploading = ref(false)
const uploadProgress = ref(0)
const selected = ref(null)
const fileInput = ref(null)
const effectiveMediaType = computed(() => props.resourceType === 'asset' ? props.mediaType : 'image')
const uploadIcon = computed(() => ({ image: ImagePlus, video: Video, audio: Music2 }[effectiveMediaType.value]))
const formatHint = computed(() => ({ image: 'JPG、PNG、WebP', video: 'MP4、MOV、WebM', audio: 'MP3、WAV、M4A' }[effectiveMediaType.value]))
const copy = computed(() => ({
  asset: { title: `选择${props.mediaType === 'video' ? '视频' : props.mediaType === 'audio' ? '音频' : '图片'}素材`, description: '从资产库选择，或上传新的素材', upload: `上传${props.mediaType === 'video' ? '视频' : props.mediaType === 'audio' ? '音频' : '图片'}` },
  model: { title: '选择模特', description: '选择系统模特或已上传的模特', upload: '上传模特' },
  character: { title: '选择角色', description: '选择系统角色或已上传的角色', upload: '上传角色' },
}[props.resourceType]))
const visibleItems = computed(() => items.value.filter((item) => {
  const queryMatches = !query.value.trim() || item.name.toLowerCase().includes(query.value.trim().toLowerCase())
  return item.mediaType === effectiveMediaType.value && queryMatches
}))

async function loadAssets() {
  loading.value = true
  try {
    const result = props.resourceType === 'asset'
      ? await listAssets(props.mediaType)
      : await listReferenceItems(props.resourceType)
    if (result.code !== 0) throw new Error(result.message)
    items.value = result.data.map((item) => normalizeLibraryItem(item, props.resourceType))
    selected.value = items.value.find((item) => item.url === props.selectedUrl) || null
  } catch (error) {
    toast.error(error.response?.data?.message || error.message || '素材加载失败')
  } finally {
    loading.value = false
  }
}

async function handleUpload(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const error = validateMediaFile(effectiveMediaType.value, file)
  if (error) return toast.warning(error)
  uploading.value = true
  uploadProgress.value = 0
  try {
    const metadata = await readMediaMetadata(effectiveMediaType.value, file)
    const result = props.resourceType === 'asset'
      ? await uploadMedia(props.mediaType, file, {
        workspaceId: props.workspaceId,
        nodeId: props.nodeId,
        ...metadata,
      }, (progress) => { uploadProgress.value = progress })
      : await uploadReferenceItem(props.resourceType, file, (progress) => { uploadProgress.value = progress })
    if (result.code !== 0) throw new Error(result.message)
    const item = normalizeLibraryItem({ ...result.data, byte_size: result.data.size }, props.resourceType)
    items.value = [item, ...items.value]
    selected.value = item
  } catch (uploadError) {
    toast.error(uploadError.response?.data?.message || uploadError.message || '素材上传失败')
  } finally {
    uploading.value = false
  }
}

function confirmSelection() {
  if (selected.value) emit('select', selected.value)
}

onMounted(loadAssets)
</script>

<template>
  <AppModal :title="copy.title" :description="copy.description" @close="emit('close')">
    <template #header-actions>
      <label class="asset-picker-search"><Search :size="15" /><AppInput v-model="query" placeholder="搜索素材" aria-label="搜索素材" /></label>
    </template>

    <EmptyState v-if="loading" title="正在加载素材" loading />
    <div v-else class="asset-picker-grid">
      <AppButton class="asset-picker-upload" :disabled="uploading" @click="fileInput?.click()">
        <LoaderCircle v-if="uploading" class="asset-picker-spinner" :size="22" />
        <component :is="uploadIcon" v-else :size="22" />
        <strong>{{ uploading ? `上传中 ${uploadProgress}%` : copy.upload }}</strong>
        <small>{{ formatHint }}</small>
      </AppButton>
      <input ref="fileInput" type="file" :accept="mediaUploadRules[effectiveMediaType]?.types.join(',')" hidden @change="handleUpload" />

      <AppButton
        v-for="item in visibleItems"
        :key="`${item.source}:${item.id}`"
        class="asset-picker-item"
        :class="{ selected: selected?.source === item.source && selected?.id === item.id }"
        :aria-pressed="selected?.source === item.source && selected?.id === item.id"
        @click="selected = item"
      >
        <img :src="buildOssImageUrl(item.url, { width: 480, quality: 80 })" :alt="item.name" loading="lazy" referrerpolicy="no-referrer" />
        <span>{{ item.name }}</span>
      </AppButton>
      <EmptyState v-if="!visibleItems.length" compact title="暂无匹配素材" />
    </div>

    <template #footer>
      <AppButton variant="soft" @click="emit('close')">取消</AppButton>
      <AppButton variant="primary" :disabled="!selected" @click="confirmSelection">使用所选素材</AppButton>
    </template>
  </AppModal>
</template>
