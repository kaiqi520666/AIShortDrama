<script setup>
import { useI18n } from 'vue-i18n'
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

const { t } = useI18n()

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
  role: { title: t('canvas.selectCharacter'), description: props.includeAssetLibrary ? t('canvas.selectCharacterIncludingAssets') : t('canvas.selectCharacterDescription'), upload: t('canvas.uploadCharacter') },
  scene: { title: t('canvas.selectScene'), description: t('canvas.selectSceneDescription'), upload: t('canvas.uploadScene') },
  asset: { title: t('canvas.selectMediaType', { p0: props.mediaType === 'video' ? t('canvas.video') : props.mediaType === 'audio' ? t('canvas.audio') : t('canvas.image') }), description: t('canvas.selectMediaDescription'), upload: t('canvas.uploadType', { p0: props.mediaType === 'video' ? t('canvas.video') : props.mediaType === 'audio' ? t('canvas.audio') : t('canvas.image') }) },
  model: { title: t('canvas.selectModel'), description: t('canvas.selectModelDescription'), upload: t('canvas.uploadModel') },
  character: { title: t('canvas.selectVirtualCharacter'), description: t('canvas.selectVirtualCharacterDescription'), upload: t('canvas.upload') },
  garment: { title: t('canvas.selectApparel'), description: t('canvas.selectApparelDescription'), upload: t('canvas.uploadApparel') },
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
    toast.error(getApiErrorMessage(error, t('canvas.mediaLoadFailed')))
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
    toast.error(getApiErrorMessage(uploadError, t('canvas.mediaUploadFailed')))
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
    else toast.info(t('canvas.characterProcessing'))
  } catch (error) {
    toast.error(getApiErrorMessage(error, t('canvas.characterRegistrationFailed')))
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
      <label class="asset-picker-search"><Search :size="15" /><AppInput v-model="query" :placeholder="t('canvas.searchMedia')" :aria-label="t('canvas.searchMedia')" /></label>
    </template>

    <EmptyState v-if="loading" :title="t('canvas.loadingMedia')" loading />
    <div v-else class="asset-picker-grid">
      <div v-if="includeAssetLibrary && resourceType === 'character'" class="asset-picker-upload asset-picker-upload-options">
        <AppButton class="asset-picker-action" :disabled="uploading" @click="fileInput?.click()">
          <LoaderCircle v-if="uploading" class="asset-picker-spinner" :size="22" />
          <ImagePlus v-else :size="22" />
          <span>{{ uploading ? t('canvas.uploadProgress', { p0: uploadProgress }) : t('canvas.upload') }}</span>
        </AppButton>
        <AppButton class="asset-picker-action" @click="emit('open-asset-library')">
          <Images :size="22" />
          <span>{{ t('canvas.media') }}</span>
        </AppButton>
      </div>
      <AppButton v-else class="asset-picker-upload" :disabled="uploading" @click="fileInput?.click()">
        <LoaderCircle v-if="uploading" class="asset-picker-spinner" :size="22" />
        <component :is="uploadIcon" v-else :size="22" />
        <strong>{{ uploading ? t('canvas.uploadProgress', { p0: uploadProgress }) : copy.upload }}</strong>
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
        <span class="asset-picker-item-label"><strong>{{ item.name }}</strong><small v-if="resourceType === 'character'">{{ registeringId === item.id ? t('canvas.registering') : item.pickerKind === 'asset' ? t('canvas.clickRegister') : ({ active: t('canvas.seedanceAvailable'), processing: t('canvas.processingRefresh'), failed: t('canvas.failedRetry'), unregistered: t('canvas.clickRegister') })[item.seedanceStatus] || '' }}</small></span>
      </AppButton>
      <EmptyState v-if="!visibleItems.length" compact :title="t('canvas.noMatchingMedia')" />
    </div>

    <template #footer>
      <AppButton variant="soft" @click="emit('close')">{{ t('canvas.cancel') }}</AppButton>
      <AppButton variant="primary" :disabled="!selected || (resourceType === 'character' && selected.seedanceStatus !== 'active')" @click="confirmSelection">{{ t('canvas.useSelectedMedia') }}</AppButton>
    </template>
  </AppModal>
</template>
