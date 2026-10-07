<script setup>
import { useI18n } from 'vue-i18n'
import { localizeAccountText } from '../../utils/accountLocalization'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ExternalLink, Eye } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { getGenerationDetail, getGenerationHistory } from '../../api/account'
import AdminDialog from '../../components/admin/AdminDialog.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { getApiErrorMessage, getTaskErrorMessage } from '../../utils/apiError'
import { buildOssImageUrl } from '../../utils/ossImage'

const { t, locale } = useI18n()
const router = useRouter()
const toast = useGlobalToast()
const loading = ref(true)
const detailLoadingId = ref('')
const detail = ref(null)
const filters = reactive({ media_type: 'all', status: 'all' })
const result = ref({ items: [], page: 1, page_size: 20, total: 0 })
const mediaOptions = computed(() => ([
  { value: 'all', label: t('records.allMedia') },
  { value: 'text', label: t('records.text') },
  { value: 'image', label: t('records.image') },
  { value: 'video', label: t('records.video') },
  { value: 'audio', label: t('records.audio') },
]))
const statusOptions = computed(() => ([
  { value: 'all', label: t('records.allStatuses') },
  { value: 'processing', label: t('records.processing') },
  { value: 'succeeded', label: t('records.success') },
  { value: 'failed', label: t('records.failed') },
]))
const statusLabels = computed(() => ({
  queued: t('records.queued'), running: t('records.running'), succeeded: t('records.success'), failed: t('records.failed'), timeout: t('records.timeout'), cancelled: t('records.cancelled'),
  needs_review: t('taskStatus.needs_review'),
}))
const columns = computed(() => ([
  { key: 'created_at', label: t('records.time'), width: '158px' },
  { key: 'workspace', label: t('records.workspace') },
  { key: 'type_label', label: t('records.mediaType'), width: '96px' },
  { key: 'model', label: t('records.model'), width: '220px', class: 'generation-model-cell' },
  { key: 'status', label: t('records.status'), width: '88px' },
  { key: 'charged_credits', label: t('records.charged'), width: '90px', align: 'right' },
  { key: 'actions', label: t('records.details'), width: '84px', align: 'right' },
]))

async function load(page = 1) {
  loading.value = true
  try {
    const response = await getGenerationHistory({ ...filters, page, page_size: 20 })
    if (response.code !== 0) throw new Error(response.message)
    result.value = response.data
  } catch (error) {
    toast.error(getApiErrorMessage(error, t('records.historyError')))
  } finally {
    loading.value = false
  }
}

async function showDetail(task) {
  detailLoadingId.value = task.id
  try {
    const response = await getGenerationDetail(task.id)
    if (response.code !== 0) throw new Error(response.message)
    detail.value = response.data
  } catch (error) {
    toast.error(getApiErrorMessage(error, t('records.detailError')))
  } finally {
    detailLoadingId.value = ''
  }
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString(locale.value, { timeZone: 'Asia/Shanghai' }) : '—'
}

function openWorkspace() {
  const workspaceId = detail.value?.workspace.available && detail.value.workspace.id
  if (workspaceId) router.push({ name: 'canvas', params: { workspaceId } })
}

watch(() => [filters.media_type, filters.status], () => load())
onMounted(load)
</script>

<template>
  <section class="account-content">
    <header class="account-section-heading"><h1>{{ t('records.history') }}</h1><p>{{ t('records.historySubtitle') }}</p></header>
    <div class="generation-filters">
      <AppSelect v-model="filters.media_type" :options="mediaOptions" :aria-label="t('records.mediaType')" />
      <AppSelect v-model="filters.status" :options="statusOptions" :aria-label="t('records.taskStatus')" />
    </div>
    <AppDataTable
      :columns="columns"
      :items="result.items"
      :loading="loading"
      :loading-title="t('records.historyLoading')"
      :empty-title="t('records.historyEmpty')"
      :empty-description="t('records.historyFilterEmpty')"
      min-width="920px"
      :pagination="{ page: result.page, pageSize: result.page_size, total: result.total }"
      @page-change="load"
    >
      <template #cell-created_at="{ value }">{{ formatDate(value) }}</template>
      <template #cell-workspace="{ value }"><span class="generation-workspace">{{ value.available ? value.name : t('records.deletedWorkspace') }}</span></template>
      <template #cell-type_label="{ item }"><span class="generation-media-type" :class="`is-${item.media_type}`">{{ localizeAccountText(item.type_label) }}</span></template>
      <template #cell-status="{ value }"><span class="generation-status" :class="`is-${value}`">{{ statusLabels[value] || value }}</span></template>
      <template #cell-charged_credits="{ value }"><strong class="generation-credits">{{ value }}</strong></template>
      <template #cell-actions="{ item }">
        <AppButton size="sm" variant="soft" :disabled="detailLoadingId === item.id" @click="showDetail(item)">
          <Eye :size="14" />{{ detailLoadingId === item.id ? t('records.loading') : t('records.view') }}
        </AppButton>
      </template>
    </AppDataTable>

    <AdminDialog
      v-if="detail"
      :title="t('records.generationDetail')"
      :description="localizeAccountText(detail.type_label)"
      :reason-required="false"
      :cancel-text="''"
      :confirm-text="t('records.close')"
      @close="detail = null"
      @submit="detail = null"
    >
      <dl class="generation-detail-summary">
        <div><dt>{{ t('records.workspace') }}</dt><dd>{{ detail.workspace.available ? detail.workspace.name : t('records.deletedWorkspace') }}</dd></div>
        <div><dt>{{ t('records.model') }}</dt><dd>{{ detail.model }}</dd></div>
        <div><dt>{{ t('records.status') }}</dt><dd><span class="generation-status" :class="`is-${detail.status}`">{{ statusLabels[detail.status] || detail.status }}</span></dd></div>
        <div><dt>{{ t('records.charged') }}</dt><dd>{{ detail.charged_credits }}</dd></div>
        <div><dt>{{ t('records.createdAt') }}</dt><dd>{{ formatDate(detail.created_at) }}</dd></div>
        <div><dt>{{ t('records.finishedAt') }}</dt><dd>{{ formatDate(detail.finished_at) }}</dd></div>
      </dl>

      <section v-if="detail.specs.length" class="generation-detail-section">
        <h3>{{ t('records.specs') }}</h3>
        <dl class="generation-specs"><div v-for="spec in detail.specs" :key="spec.label"><dt>{{ localizeAccountText(spec.label) }}</dt><dd>{{ localizeAccountText(spec.value) }}</dd></div></dl>
      </section>
      <section class="generation-detail-section"><h3>{{ t('records.prompt') }}</h3><p class="generation-prompt">{{ detail.prompt || '—' }}</p></section>
      <section v-if="detail.error_message" class="generation-detail-section generation-detail-error"><h3>{{ $t('errors.failure_reason') }}</h3><p>{{ getTaskErrorMessage(detail) }}</p></section>
      <section v-if="detail.result" class="generation-detail-section">
        <h3>{{ t('records.result') }}</h3>
        <p v-if="detail.result.type === 'text'" class="generation-result-text">{{ detail.result.content }}</p>
        <img v-else-if="detail.result.type === 'image'" class="generation-result-image" :src="buildOssImageUrl(detail.result.url)" :alt="t('records.result')" />
        <video v-else-if="detail.result.type === 'video'" class="generation-result-media" :src="detail.result.url" controls preload="metadata" />
        <audio v-else-if="detail.result.type === 'audio'" class="generation-result-audio" :src="detail.result.url" controls preload="metadata" />
      </section>
      <AppButton v-if="detail.status === 'succeeded' && detail.workspace.available" variant="soft" @click="openWorkspace">
        <ExternalLink :size="15" />{{ t('records.openWorkspace') }}
      </AppButton>
    </AdminDialog>
  </section>
</template>
