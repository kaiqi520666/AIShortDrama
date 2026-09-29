<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
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

const router = useRouter()
const toast = useGlobalToast()
const loading = ref(true)
const detailLoadingId = ref('')
const detail = ref(null)
const filters = reactive({ media_type: 'all', status: 'all' })
const result = ref({ items: [], page: 1, page_size: 20, total: 0 })
const mediaOptions = [
  { value: 'all', label: '全部模型类型' },
  { value: 'text', label: '文本' },
  { value: 'image', label: '图片' },
  { value: 'video', label: '视频' },
  { value: 'audio', label: '音频' },
]
const statusOptions = [
  { value: 'all', label: '全部状态' },
  { value: 'processing', label: '进行中' },
  { value: 'succeeded', label: '成功' },
  { value: 'failed', label: '失败' },
]
const statusLabels = {
  queued: '排队中', running: '生成中', succeeded: '成功', failed: '失败', timeout: '已超时', cancelled: '已取消',
}
const columns = [
  { key: 'created_at', label: '时间', width: '158px' },
  { key: 'workspace', label: '工作台' },
  { key: 'type_label', label: '模型类型', width: '96px' },
  { key: 'model', label: '模型', width: '220px', class: 'generation-model-cell' },
  { key: 'status', label: '状态', width: '88px' },
  { key: 'charged_credits', label: '消耗积分', width: '90px', align: 'right' },
  { key: 'actions', label: '详情', width: '84px', align: 'right' },
]

async function load(page = 1) {
  loading.value = true
  try {
    const response = await getGenerationHistory({ ...filters, page, page_size: 20 })
    if (response.code !== 0) throw new Error(response.message)
    result.value = response.data
  } catch (error) {
    toast.error(getApiErrorMessage(error, '生成记录加载失败'))
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
    toast.error(getApiErrorMessage(error, '任务详情加载失败'))
  } finally {
    detailLoadingId.value = ''
  }
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '—'
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
    <header class="account-section-heading"><h1>生成记录</h1><p>查看生成状态、积分消耗与结果</p></header>
    <div class="generation-filters">
      <AppSelect v-model="filters.media_type" :options="mediaOptions" aria-label="模型类型" />
      <AppSelect v-model="filters.status" :options="statusOptions" aria-label="任务状态" />
    </div>
    <AppDataTable
      :columns="columns"
      :items="result.items"
      :loading="loading"
      loading-title="正在加载生成记录"
      empty-title="暂无生成记录"
      empty-description="当前筛选条件下没有相关任务"
      min-width="920px"
      :pagination="{ page: result.page, pageSize: result.page_size, total: result.total }"
      @page-change="load"
    >
      <template #cell-created_at="{ value }">{{ formatDate(value) }}</template>
      <template #cell-workspace="{ value }"><span class="generation-workspace">{{ value.name }}</span></template>
      <template #cell-type_label="{ item }"><span class="generation-media-type" :class="`is-${item.media_type}`">{{ item.type_label }}</span></template>
      <template #cell-status="{ value }"><span class="generation-status" :class="`is-${value}`">{{ statusLabels[value] || value }}</span></template>
      <template #cell-charged_credits="{ value }"><strong class="generation-credits">{{ value }}</strong></template>
      <template #cell-actions="{ item }">
        <AppButton size="sm" variant="soft" :disabled="detailLoadingId === item.id" @click="showDetail(item)">
          <Eye :size="14" />{{ detailLoadingId === item.id ? '加载中' : '查看' }}
        </AppButton>
      </template>
    </AppDataTable>

    <AdminDialog
      v-if="detail"
      title="生成详情"
      :description="detail.type_label"
      :reason-required="false"
      :cancel-text="''"
      confirm-text="关闭"
      @close="detail = null"
      @submit="detail = null"
    >
      <dl class="generation-detail-summary">
        <div><dt>工作台</dt><dd>{{ detail.workspace.name }}</dd></div>
        <div><dt>模型</dt><dd>{{ detail.model }}</dd></div>
        <div><dt>状态</dt><dd><span class="generation-status" :class="`is-${detail.status}`">{{ statusLabels[detail.status] || detail.status }}</span></dd></div>
        <div><dt>消耗积分</dt><dd>{{ detail.charged_credits }}</dd></div>
        <div><dt>创建时间</dt><dd>{{ formatDate(detail.created_at) }}</dd></div>
        <div><dt>完成时间</dt><dd>{{ formatDate(detail.finished_at) }}</dd></div>
      </dl>

      <section v-if="detail.specs.length" class="generation-detail-section">
        <h3>生成规格</h3>
        <dl class="generation-specs"><div v-for="spec in detail.specs" :key="spec.label"><dt>{{ spec.label }}</dt><dd>{{ spec.value }}</dd></div></dl>
      </section>
      <section class="generation-detail-section"><h3>提示词</h3><p class="generation-prompt">{{ detail.prompt || '—' }}</p></section>
      <section v-if="detail.error_message" class="generation-detail-section generation-detail-error"><h3>{{ $t('errors.failure_reason') }}</h3><p>{{ getTaskErrorMessage(detail) }}</p></section>
      <section v-if="detail.result" class="generation-detail-section">
        <h3>生成结果</h3>
        <p v-if="detail.result.type === 'text'" class="generation-result-text">{{ detail.result.content }}</p>
        <img v-else-if="detail.result.type === 'image'" class="generation-result-image" :src="buildOssImageUrl(detail.result.url)" alt="生成结果" />
        <video v-else-if="detail.result.type === 'video'" class="generation-result-media" :src="detail.result.url" controls preload="metadata" />
        <audio v-else-if="detail.result.type === 'audio'" class="generation-result-audio" :src="detail.result.url" controls preload="metadata" />
      </section>
      <AppButton v-if="detail.status === 'succeeded' && detail.workspace.available" variant="soft" @click="openWorkspace">
        <ExternalLink :size="15" />打开工作台
      </AppButton>
    </AdminDialog>
  </section>
</template>
