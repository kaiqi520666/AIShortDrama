<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Copy, Eye, RefreshCw, Search } from 'lucide-vue-next'
import { getAdminTask, getAdminTaskProviderStatus, getAdminTasks } from '../../api/admin'
import AdminDialog from '../../components/admin/AdminDialog.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDateTime from '../../components/ui/AppDateTime.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { getApiErrorMessage } from '../../utils/apiError'
import { taskDiagnosticSummary, taskStageLabel } from '../../utils/taskDiagnostic'

const toast = useGlobalToast()
const loading = ref(false)
const detailLoadingId = ref('')
const detail = ref(null)
const providerState = ref(null)
const providerLoading = ref(false)
const data = reactive({ items: [], page: 1, page_size: 20, total: 0 })
const filters = reactive({ q: '', media_type: 'all', model: '', status: '', start_at: '', end_at: '' })
const mediaOptions = [{ value: 'all', label: '全部类型' }, ...['text', 'image', 'video', 'audio'].map((value) => ({ value, label: ({ text: '文本', image: '图片', video: '视频', audio: '音频' })[value] }))]
const columns = [
  { key: 'user', label: '用户' },
  { key: 'task_type', label: '类型' },
  { key: 'model', label: '模型', class: 'admin-model-cell' },
  { key: 'status', label: '状态' },
  { key: 'credits', label: '积分' },
  { key: 'created_at', label: '创建时间' },
  { key: 'actions', label: '详情' },
]
async function load(page = 1) { loading.value = true; try { const params = { ...filters, page, page_size: data.page_size }; if (!params.start_at) delete params.start_at; if (!params.end_at) delete params.end_at; const result = await getAdminTasks(params); if (result.code !== 0) throw new Error(result.message); Object.assign(data, result.data) } catch (error) { toast.error(getApiErrorMessage(error, '任务加载失败')) } finally { loading.value = false } }
async function openDetail(task) {
  detailLoadingId.value = task.id
  try {
    const result = await getAdminTask(task.id)
    if (result.code !== 0) throw new Error(result.message)
    detail.value = result.data
    providerState.value = null
  } catch (error) {
    toast.error(getApiErrorMessage(error, '任务详情加载失败'))
  } finally {
    detailLoadingId.value = ''
  }
}
async function refreshProviderStatus() {
  providerLoading.value = true
  try {
    const result = await getAdminTaskProviderStatus(detail.value.id)
    if (result.code !== 0) throw new Error(result.message)
    providerState.value = result.data
  } catch (error) {
    toast.error(getApiErrorMessage(error, '上游状态查询失败'))
  } finally {
    providerLoading.value = false
  }
}
async function copyId(value, label) {
  try {
    await navigator.clipboard.writeText(value)
    toast.success(`${label}已复制`)
  } catch {
    toast.error('复制失败')
  }
}
function formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '—' }
function parseEmbeddedJson(value) {
  if (typeof value !== 'string') return value
  const source = value.trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '')
  const opening = source[0]
  const closing = opening === '{' ? '}' : opening === '[' ? ']' : ''
  if (!closing) return value
  const end = source.lastIndexOf(closing)
  try { return JSON.parse(source.slice(0, end + 1)) } catch { return value }
}
function normalizeSnapshot(value) {
  const parsed = parseEmbeddedJson(value)
  if (Array.isArray(parsed)) return parsed.map(normalizeSnapshot)
  if (parsed && typeof parsed === 'object') return Object.fromEntries(Object.entries(parsed).map(([key, item]) => [key, normalizeSnapshot(item)]))
  return parsed
}
function formatSnapshot(value) {
  return JSON.stringify(normalizeSnapshot(value ?? {}), null, 2)
}
onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>GENERATION MONITOR</span><h1>生成任务</h1><p>查询全部生成任务与计费快照</p></div><b>{{ data.total }} 个任务</b></header>
    <form class="admin-filters admin-filters--wide" @submit.prevent="load(1)"><label class="admin-search"><Search :size="15" /><AppInput v-model="filters.q" placeholder="用户名或邮箱" /></label><AppSelect v-model="filters.media_type" :options="mediaOptions" aria-label="任务类型" /><AppInput v-model="filters.model" placeholder="模型名称" /><AppInput v-model="filters.status" placeholder="任务状态" /><AppDateTime v-model="filters.start_at" aria-label="开始时间" placeholder="开始时间" /><AppDateTime v-model="filters.end_at" aria-label="结束时间" placeholder="结束时间" /><AppButton type="submit" variant="primary">查询</AppButton></form>
    <AppDataTable :columns="columns" :items="data.items" :loading="loading" loading-title="正在加载生成任务" empty-title="没有符合条件的任务" min-width="900px" :pagination="{ page: data.page, pageSize: data.page_size, total: data.total }" @page-change="load">
      <template #cell-user="{ item: task }"><strong>{{ task.user.username }}</strong><small>{{ task.user.email }}</small></template>
      <template #cell-status="{ item: task }"><div class="admin-task-status"><span class="admin-status" :class="`is-${task.status}`">{{ task.status }}</span><small v-if="task.diagnostic_summary" :title="task.diagnostic_summary.provider_message">{{ taskDiagnosticSummary(task.diagnostic_summary) }}</small></div></template>
      <template #cell-credits="{ item: task }">{{ task.charged_credits }} / {{ task.frozen_credits }}</template>
      <template #cell-created_at="{ value }">{{ formatDate(value) }}</template>
      <template #cell-actions="{ item: task }"><AppButton size="sm" variant="soft" :disabled="detailLoadingId === task.id" @click="openDetail(task)"><Eye :size="14" />{{ detailLoadingId === task.id ? '加载中' : '查看' }}</AppButton></template>
    </AppDataTable>
    <AdminDialog v-if="detail" title="任务详情" :description="detail.id" :reason-required="false" confirm-text="关闭" @close="detail = null" @submit="detail = null">
      <section v-if="detail.diagnostic_snapshot" class="admin-task-diagnostic">
        <header><div><strong>失败诊断</strong><span>{{ taskDiagnosticSummary(detail.diagnostic_snapshot) }}</span></div><span class="admin-status" :class="detail.diagnostic_snapshot.retryable ? 'is-running' : 'is-failed'">{{ detail.diagnostic_snapshot.retryable ? '可重试' : '不可重试' }}</span></header>
        <dl class="admin-detail-list">
          <div><dt>错误阶段</dt><dd>{{ taskStageLabel(detail.diagnostic_snapshot.stage) }}</dd></div>
          <div><dt>上游状态</dt><dd>{{ detail.diagnostic_snapshot.provider_status ? `HTTP ${detail.diagnostic_snapshot.provider_status}` : '—' }}</dd></div>
          <div><dt>异常类型</dt><dd>{{ detail.diagnostic_snapshot.exception_type || '—' }}</dd></div>
          <div><dt>发生时间</dt><dd>{{ formatDate(detail.diagnostic_snapshot.occurred_at) }}</dd></div>
        </dl>
        <p>{{ detail.diagnostic_snapshot.provider_message || detail.error_message }}</p>
      </section>
      <dl class="admin-detail-list">
        <div><dt>状态</dt><dd>{{ detail.status }} · {{ detail.progress }}%</dd></div>
        <div><dt>用户错误</dt><dd>{{ detail.error_message || '—' }}</dd></div>
        <div class="admin-copy-field"><dt>任务 ID</dt><dd><code>{{ detail.id }}</code><AppButton icon-only size="sm" variant="soft" title="复制任务 ID" aria-label="复制任务 ID" @click="copyId(detail.id, '任务 ID')"><Copy :size="14" /></AppButton></dd></div>
        <div class="admin-copy-field"><dt>Provider 任务 ID</dt><dd><code>{{ detail.provider_task_id || '—' }}</code><AppButton v-if="detail.provider_task_id" icon-only size="sm" variant="soft" title="复制 Provider 任务 ID" aria-label="复制 Provider 任务 ID" @click="copyId(detail.provider_task_id, 'Provider 任务 ID')"><Copy :size="14" /></AppButton></dd></div>
        <div v-if="detail.diagnostic_snapshot?.provider_request_id" class="admin-copy-field"><dt>Request ID</dt><dd><code>{{ detail.diagnostic_snapshot.provider_request_id }}</code><AppButton icon-only size="sm" variant="soft" title="复制 Request ID" aria-label="复制 Request ID" @click="copyId(detail.diagnostic_snapshot.provider_request_id, 'Request ID')"><Copy :size="14" /></AppButton></dd></div>
      </dl>
      <section v-if="detail.provider === 'toapis' && detail.provider_task_id && ['image', 'video'].includes(detail.task_type)" class="admin-provider-query">
        <AppButton size="sm" variant="soft" :disabled="providerLoading" @click="refreshProviderStatus"><RefreshCw :size="14" :class="{ 'is-spinning': providerLoading }" />{{ providerLoading ? '查询中' : '重新查询上游状态' }}</AppButton>
        <p v-if="providerState"><strong>{{ providerState.status }}</strong> · {{ providerState.progress }}%<span v-if="providerState.error_message"> · {{ providerState.error_message }}</span><small>查询于 {{ formatDate(providerState.checked_at) }}</small></p>
      </section>
      <details v-if="detail.diagnostic_snapshot" class="admin-task-snapshot"><summary>完整错误</summary><pre class="admin-json">{{ formatSnapshot(detail.diagnostic_snapshot) }}</pre></details>
      <details class="admin-task-snapshot"><summary>请求快照</summary><pre class="admin-json">{{ formatSnapshot(detail.request_snapshot) }}</pre></details>
      <details class="admin-task-snapshot"><summary>计费快照</summary><pre class="admin-json">{{ formatSnapshot(detail.pricing_snapshot) }}</pre></details>
      <details class="admin-task-snapshot"><summary>结果快照</summary><pre class="admin-json">{{ formatSnapshot(detail.result) }}</pre></details>
    </AdminDialog>
  </section>
</template>
