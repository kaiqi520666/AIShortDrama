<script setup>
import { computed, onMounted, ref } from 'vue'
import { ImagePlus, LoaderCircle, Search } from 'lucide-vue-next'
import { listAssets } from '../../api/assets'
import { uploadMedia } from '../../api/uploads'
import { imageAssetCategories, normalizeAssetItem, systemImageAssets } from '../../config/assetLibrary'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { buildOssImageUrl } from '../../utils/ossImage'
import { mediaUploadRules, readMediaMetadata, validateMediaFile } from '../../utils/mediaFiles'
import AppButton from '../ui/AppButton.vue'
import AppInput from '../ui/AppInput.vue'
import AppModal from '../ui/AppModal.vue'
import AppTabs from '../ui/AppTabs.vue'
import EmptyState from '../ui/EmptyState.vue'

const props = defineProps({
  mediaType: { type: String, default: 'image' },
  category: { type: String, default: '' },
  workspaceId: { type: String, required: true },
  nodeId: { type: String, required: true },
  selectedUrl: { type: String, default: '' },
})
const emit = defineEmits(['close', 'select'])
const toast = useGlobalToast()
const activeCategory = ref(props.category || 'all')
const query = ref('')
const userAssets = ref([])
const loading = ref(true)
const uploading = ref(false)
const uploadProgress = ref(0)
const selected = ref(null)
const fileInput = ref(null)
const categoryOptions = computed(() => props.category
  ? imageAssetCategories.filter((item) => item.value === props.category)
  : imageAssetCategories)
const allAssets = computed(() => [
  ...userAssets.value,
  ...(props.mediaType === 'image' ? systemImageAssets : []),
])
const visibleAssets = computed(() => allAssets.value.filter((item) => {
  const categoryMatches = activeCategory.value === 'all' || item.category === activeCategory.value
  const queryMatches = !query.value.trim() || item.name.toLowerCase().includes(query.value.trim().toLowerCase())
  return item.mediaType === props.mediaType && categoryMatches && queryMatches
}))
const uploadCategory = computed(() => activeCategory.value === 'all' ? 'general' : activeCategory.value)
const uploadLabel = computed(() => uploadCategory.value === 'model' ? '上传模特' : uploadCategory.value === 'character' ? '上传角色' : '上传图片')

async function loadAssets() {
  loading.value = true
  try {
    const result = await listAssets(props.mediaType)
    if (result.code !== 0) throw new Error(result.message)
    userAssets.value = result.data.map(normalizeAssetItem)
    selected.value = allAssets.value.find((item) => item.url === props.selectedUrl) || null
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
  const error = validateMediaFile(props.mediaType, file)
  if (error) return toast.warning(error)
  uploading.value = true
  uploadProgress.value = 0
  try {
    const metadata = await readMediaMetadata(props.mediaType, file)
    const result = await uploadMedia(props.mediaType, file, {
      workspaceId: props.workspaceId,
      nodeId: props.nodeId,
      category: uploadCategory.value,
      ...metadata,
    }, (progress) => { uploadProgress.value = progress })
    if (result.code !== 0) throw new Error(result.message)
    const item = normalizeAssetItem({ ...result.data, byte_size: result.data.size })
    userAssets.value = [item, ...userAssets.value]
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
  <AppModal title="选择图片素材" description="从素材库选择，或上传新的图片" @close="emit('close')">
    <div class="asset-picker-toolbar">
      <AppTabs v-if="!category" v-model="activeCategory" :options="categoryOptions" aria-label="图片素材分类" />
      <label class="asset-picker-search"><Search :size="15" /><AppInput v-model="query" placeholder="搜索素材" aria-label="搜索素材" /></label>
    </div>

    <EmptyState v-if="loading" title="正在加载素材" loading />
    <div v-else class="asset-picker-grid">
      <AppButton class="asset-picker-upload" :disabled="uploading" @click="fileInput?.click()">
        <LoaderCircle v-if="uploading" class="asset-picker-spinner" :size="22" />
        <ImagePlus v-else :size="22" />
        <strong>{{ uploading ? `上传中 ${uploadProgress}%` : uploadLabel }}</strong>
        <small>JPG、PNG、WebP</small>
      </AppButton>
      <input ref="fileInput" type="file" :accept="mediaUploadRules[mediaType]?.types.join(',')" hidden @change="handleUpload" />

      <AppButton
        v-for="item in visibleAssets"
        :key="`${item.source}:${item.id}`"
        class="asset-picker-item"
        :class="{ selected: selected?.source === item.source && selected?.id === item.id }"
        :aria-pressed="selected?.source === item.source && selected?.id === item.id"
        @click="selected = item"
      >
        <img :src="buildOssImageUrl(item.url, { width: 480, quality: 80 })" :alt="item.name" loading="lazy" referrerpolicy="no-referrer" />
        <span>{{ item.name }}</span>
      </AppButton>
      <EmptyState v-if="!visibleAssets.length" compact title="暂无匹配素材" />
    </div>

    <template #footer>
      <AppButton variant="soft" @click="emit('close')">取消</AppButton>
      <AppButton variant="primary" :disabled="!selected" @click="confirmSelection">使用所选素材</AppButton>
    </template>
  </AppModal>
</template>
