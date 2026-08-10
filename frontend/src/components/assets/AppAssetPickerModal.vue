<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ImagePlus, Images, LoaderCircle, Music2, Search, Video } from 'lucide-vue-next'
import { listAssets } from '../../api/assets'
import { createCharacterFromAsset, listReferenceItems, registerCharacter, uploadReferenceItem } from '../../api/referenceLibrary'
import { uploadMedia } from '../../api/uploads'
import { normalizeLibraryItem } from '../../config/assetLibrary'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { getApiErrorMessage } from '../../utils/apiError'
import { buildOssImageUrl } from '../../utils/ossImage'
import { mediaUploadRules, readMediaMetadata, validateMediaFile } from '../../utils/mediaFiles'
import AppButton from '../ui/AppButton.vue'
import AppImageHoverPreview from '../ui/AppImageHoverPreview.vue'
import AppInput from '../ui/AppInput.vue'
import AppModal from '../ui/AppModal.vue'
import EmptyState from '../ui/EmptyState.vue'

const props = defineProps({
  resourceType: { type: String, default: 'asset', validator: (value) => ['asset', 'model', 'character', 'garment', 'scene'].includes(value) },
  mediaType: { type: String, default: 'image' },
  inputRole: { type: String, default: '' },
  workspaceId: { type: String, default: '' },
  nodeId: { type: String, default: '' },
  selectedUrl: { type: String, default: '' },
  includeAssetLibrary: Boolean,
  extraItem: { type: Object, default: null },
})
const emit = defineEmits(['close', 'select', 'open-asset-library'])
const toast = useGlobalToast()
const query = ref('')
const items = ref([])
const loading = ref(true)
const uploading = ref(false)
const registeringId = ref('')
const uploadProgress = ref(0)
const selected = ref(null)
const fileInput = ref(null)
const effectiveMediaType = computed(() => props.resourceType === 'asset' ? props.mediaType : 'image')
const uploadIcon = computed(() => ({ image: ImagePlus, video: Video, audio: Music2 }[effectiveMediaType.value]))
const formatHint = computed(() => ({ image: 'JPG、PNG、WebP', video: 'MP4、MOV、WebM', audio: 'MP3、WAV、M4A' }[effectiveMediaType.value]))
const copy = computed(() => ({
  role: { title: '选择角色', description: props.includeAssetLibrary ? '选择系统角色、已上传的角色或普通图片资产' : '选择系统角色或已上传的角色', upload: '上传角色' },
  scene: { title: '选择场景', description: '选择系统场景或已上传的场景', upload: '上传场景' },
  asset: { title: `选择${props.mediaType === 'video' ? '视频' : props.mediaType === 'audio' ? '音频' : '图片'}素材`, description: '从资产库选择，或上传新的素材', upload: `上传${props.mediaType === 'video' ? '视频' : props.mediaType === 'audio' ? '音频' : '图片'}` },
  model: { title: '选择模特', description: '选择系统模特或已上传的模特', upload: '上传模特' },
  character: { title: '选择虚拟角色', description: '选择已注册的虚拟角色，或从资产库选择普通图片', upload: '上传' },
  garment: { title: '选择服饰', description: '选择系统服饰或已上传的服饰', upload: '上传服饰' },
}[props.inputRole || props.resourceType]))
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
    const libraryItems = result.data.map((item) => ({ ...normalizeLibraryItem(item, props.resourceType), pickerKind: props.resourceType }))
    items.value = props.resourceType === 'character' ? [props.extraItem, ...libraryItems].filter(Boolean) : libraryItems
    selected.value = items.value.find((item) => item.url === props.selectedUrl) || null
  } catch (error) {
    toast.error(getApiErrorMessage(error, '素材加载失败'))
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
    const item = { ...normalizeLibraryItem({ ...result.data, byte_size: result.data.size }, props.resourceType), pickerKind: props.resourceType }
    items.value = [item, ...items.value]
    selected.value = props.resourceType === 'character' && item.seedanceStatus !== 'active' ? null : item
  } catch (uploadError) {
    toast.error(getApiErrorMessage(uploadError, '素材上传失败'))
  } finally {
    uploading.value = false
  }
}

async function selectItem(item) {
  if (registeringId.value) return
  if (props.resourceType !== 'character' || (item.pickerKind !== 'asset' && item.seedanceStatus === 'active')) {
    selected.value = item
    return
  }
  if (!['character', 'asset'].includes(item.pickerKind)) return
  registeringId.value = item.id
  try {
    const result = item.pickerKind === 'asset'
      ? await createCharacterFromAsset(item.assetId || item.id)
      : await registerCharacter(item.id)
    if (result.code !== 0) throw new Error(result.message)
    const refreshed = { ...normalizeLibraryItem(result.data || item, 'character'), pickerKind: 'character' }
    items.value = items.value.map((value) => value.id === item.id ? refreshed : value)
    if (refreshed.seedanceStatus === 'active') selected.value = refreshed
    else toast.info('角色正在处理中，请稍后点击刷新')
  } catch (error) {
    toast.error(getApiErrorMessage(error, '角色注册失败'))
  } finally {
    registeringId.value = ''
  }
}

function confirmSelection() {
  if (selected.value) emit('select', selected.value)
}

onMounted(loadAssets)

watch(() => props.extraItem, (extraItem) => {
  if (props.resourceType !== 'character') return
  const libraryItems = items.value.filter((item) => item.pickerKind !== 'asset')
  items.value = [extraItem, ...libraryItems].filter(Boolean)
  selected.value = items.value.find((item) => item.url === props.selectedUrl) || null
}, { deep: true })
</script>

<template>
  <AppModal :title="copy.title" :description="copy.description" @close="emit('close')">
    <template #header-actions>
      <label class="asset-picker-search"><Search :size="15" /><AppInput v-model="query" placeholder="搜索素材" aria-label="搜索素材" /></label>
    </template>

    <EmptyState v-if="loading" title="正在加载素材" loading />
    <div v-else class="asset-picker-grid">
      <div v-if="includeAssetLibrary && resourceType === 'character'" class="asset-picker-upload asset-picker-upload-options">
        <AppButton class="asset-picker-action" :disabled="uploading" @click="fileInput?.click()">
          <LoaderCircle v-if="uploading" class="asset-picker-spinner" :size="22" />
          <ImagePlus v-else :size="22" />
          <span>{{ uploading ? `上传中 ${uploadProgress}%` : '上传' }}</span>
        </AppButton>
        <AppButton class="asset-picker-action" @click="emit('open-asset-library')">
          <Images :size="22" />
          <span>素材</span>
        </AppButton>
      </div>
      <AppButton v-else class="asset-picker-upload" :disabled="uploading" @click="fileInput?.click()">
        <LoaderCircle v-if="uploading" class="asset-picker-spinner" :size="22" />
        <component :is="uploadIcon" v-else :size="22" />
        <strong>{{ uploading ? `上传中 ${uploadProgress}%` : copy.upload }}</strong>
        <small>{{ formatHint }}</small>
      </AppButton>
      <input ref="fileInput" type="file" :accept="mediaUploadRules[effectiveMediaType]?.types.join(',')" hidden @change="handleUpload" />

      <AppButton
        v-for="item in visibleItems"
        :key="`${item.pickerKind}:${item.source}:${item.id}`"
        class="asset-picker-item"
        :class="{ selected: selected?.pickerKind === item.pickerKind && selected?.source === item.source && selected?.id === item.id, unavailable: resourceType === 'character' && item.seedanceStatus !== 'active' }"
        :aria-pressed="selected?.pickerKind === item.pickerKind && selected?.source === item.source && selected?.id === item.id"
        @click="selectItem(item)"
      >
        <AppImageHoverPreview :src="item.url" :preview-src="buildOssImageUrl(item.url, { width: 1200, quality: 90 })" :alt="item.name">
          <img :src="buildOssImageUrl(item.url, { width: 480, quality: 80 })" :alt="item.name" loading="lazy" referrerpolicy="no-referrer" />
        </AppImageHoverPreview>
        <span class="asset-picker-item-label"><strong>{{ item.name }}</strong><small v-if="resourceType === 'character'">{{ registeringId === item.id ? '注册中' : item.pickerKind === 'asset' ? '点击注册' : ({ active: 'Seedance 可用', processing: '处理中，点击刷新', failed: '失败，点击重试', unregistered: '点击注册' })[item.seedanceStatus] || '' }}</small></span>
      </AppButton>
      <EmptyState v-if="!visibleItems.length" compact title="暂无匹配素材" />
    </div>

    <template #footer>
      <AppButton variant="soft" @click="emit('close')">取消</AppButton>
      <AppButton variant="primary" :disabled="!selected || (resourceType === 'character' && selected.seedanceStatus !== 'active')" @click="confirmSelection">使用所选素材</AppButton>
    </template>
  </AppModal>
</template>
