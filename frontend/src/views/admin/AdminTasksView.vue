<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDateTime } from '../../i18n'
import { ClipboardCheck, Copy, Eye, RefreshCw, Search } from 'lucide-vue-next'
import { getAdminTask, getAdminTaskProviderStatus, getAdminTasks } from '../../api/admin'
import AdminDialog from '../../components/admin/AdminDialog.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDateTime from '../../components/ui/AppDateTime.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { useAdminTaskReview } from '../../composables/useAdminTaskReview'
import { getApiErrorMessage, getTaskErrorMessage } from '../../utils/apiError'

const toast = useGlobalToast()
const { t, n, te } = useI18n()
const loading = ref(false)
const detailLoadingId = ref('')
const detail = ref(null)
const providerState = ref(null)
const providerLoading = ref(false)
const data = reactive({ items: [], page: 1, page_size: 20, total: 0 })
const filters = reactive({ q: '', media_type: 'all', model: '', status: '', start_at: '', end_at: '' })
const { review, openReview, closeReview, submitReview } = useAdminTaskReview({
  async onResolved(task) {
    if (detail.value?.id === task.id) detail.value = task
    providerState.value = null
    await load(data.page)
  },
})
const reviewActionOptions = computed(() => ['resume', 'fail', 'cancel'].map((value) => ({
  value,
  label: t(`admin.tasks.reviewActions.${value}`),
  disabled: value === 'resume' && !['image', 'video', 'audio'].includes(review.task?.task_type),
})))
const mediaOptions = computed(() => [{ value: 'all', label: t('admin.tasks.allTypes') }, ...['text', 'image', 'video', 'audio'].map((value) => ({ value, label: t(`home.${value}`) }))])
const columns = computed(() => [
  { key: 'user', label: t('common.user') },
  { key: 'task_type', label: t('admin.tasks.type') },
  { key: 'model', label: t('admin.model'), class: 'admin-model-cell' },
  { key: 'status', label: t('admin.status') },
  { key: 'credits', label: t('admin.tasks.credits') },
  { key: 'created_at', label: t('common.createdAt') },
  { key: 'actions', label: t('admin.actions') },
])
const statusOptions = computed(() => [{ value: '', label: t('admin.allStatuses') }, ...['queued', 'running', 'succeeded', 'failed', 'timeout', 'cancelled', 'needs_review'].map((value) => ({ value, label: t(`taskStatus.${value}`) }))])
function statusLabel(value) { return te(`taskStatus.${value}`) ? t(`taskStatus.${value}`) : value }
async function load(page = 1) { loading.value = true; try { const params = { ...filters, page, page_size: data.page_size }; if (!params.start_at) delete params.start_at; if (!params.end_at) delete params.end_at; const result = await getAdminTasks(params); if (result.code !== 0) throw new Error(result.message); Object.assign(data, result.data) } catch (error) { toast.error(getApiErrorMessage(error, t('admin.tasks.loadFailed'))) } finally { loading.value = false } }
async function openDetail(task) {
  detailLoadingId.value = task.id
  try {
    const result = await getAdminTask(task.id)
    if (result.code !== 0) throw new Error(result.message)
    detail.value = result.data
    providerState.value = null
  } catch (error) {
    toast.error(getApiErrorMessage(error, t('admin.tasks.detailFailed')))
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
    toast.error(getApiErrorMessage(error, t('admin.tasks.providerFailed')))
  } finally {
    providerLoading.value = false
  }
}
async function resolveReview() {
  try {
    if (await submitReview()) toast.success(t('admin.completed'))
  } catch (error) {
    toast.error(getApiErrorMessage(error, t('admin.tasks.reviewFailed')))
  }
}
async function copyId(value, label) {
  try {
    await navigator.clipboard.writeText(value)
    toast.success(t('admin.tasks.copied', { label }))
  } catch {
    toast.error(t('admin.tasks.copyFailed'))
  }
}
function formatDate(value) { return value ? formatDateTime(value, { timeZone: 'Asia/Shanghai', dateStyle: 'short', timeStyle: 'medium' }) : '—' }
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
  return JSON.stringify(normalizeSnapshot(value ?? {}), null, 2).replace(/\\r\\n|\\n|\\r/g, '\n')
}
onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>{{ t('navigation.operations') }}</span><h1>{{ t('navigation.tasks') }}</h1><p>{{ t('admin.tasks.description') }}</p></div><b>{{ t('admin.overview.tasks', { count: n(data.total) }) }}</b></header>
    <form class="admin-filters admin-filters--wide" @submit.prevent="load(1)"><label class="admin-search"><Search :size="15" /><AppInput v-model="filters.q" :placeholder="t('admin.users.search')" /></label><AppSelect v-model="filters.media_type" :options="mediaOptions" :aria-label="t('admin.tasks.type')" /><AppInput v-model="filters.model" :placeholder="t('admin.tasks.modelName')" /><AppSelect v-model="filters.status" :options="statusOptions" :aria-label="t('admin.overview.taskStatus')" /><AppDateTime v-model="filters.start_at" :aria-label="t('common.startTime')" :placeholder="t('common.startTime')" /><AppDateTime v-model="filters.end_at" :aria-label="t('common.endTime')" :placeholder="t('common.endTime')" /><AppButton type="submit" variant="primary">{{ t('admin.query') }}</AppButton></form>
    <AppDataTable :columns="columns" :items="data.items" :loading="loading" :loading-title="t('admin.tasks.loading')" :empty-title="t('admin.tasks.empty')" min-width="900px" :pagination="{ page: data.page, pageSize: data.page_size, total: data.total }" @page-change="load">
      <template #cell-user="{ item: task }"><strong>{{ task.user.username }}</strong><small>{{ task.user.email }}</small></template>
      <template #cell-task_type="{ value }">{{ t(`home.${value}`) }}</template>
      <template #cell-status="{ item: task }"><span class="admin-status" :class="`is-${task.status}`">{{ statusLabel(task.status) }}</span></template>
      <template #cell-credits="{ item: task }">{{ n(task.charged_credits) }} / {{ n(task.frozen_credits) }}</template>
      <template #cell-created_at="{ value }">{{ formatDate(value) }}</template>
      <template #cell-actions="{ item: task }">
        <div class="admin-table-actions">
          <AppButton size="sm" variant="soft" :disabled="detailLoadingId === task.id" @click="openDetail(task)"><Eye :size="14" />{{ t(detailLoadingId === task.id ? 'common.loading' : 'common.view') }}</AppButton>
          <AppButton v-if="task.status === 'needs_review'" size="sm" variant="soft" @click="openReview(task)"><ClipboardCheck :size="14" />{{ t('admin.tasks.resolveReview') }}</AppButton>
        </div>
      </template>
    </AppDataTable>
    <AdminDialog v-if="detail && !review.task" :title="t('admin.tasks.detail')" :description="detail.id" :reason-required="false" :confirm-text="t('common.close')" @close="detail = null" @submit="detail = null">
      <dl class="admin-detail-list">
        <div><dt>{{ t('admin.status') }}</dt><dd>{{ statusLabel(detail.status) }} · {{ n(detail.progress / 100, { style: 'percent' }) }}</dd></div>
        <div><dt>{{ t('admin.tasks.userError') }}</dt><dd>{{ detail.error_message ? getTaskErrorMessage(detail) : '—' }}</dd></div>
        <div class="admin-copy-field"><dt>{{ t('admin.tasks.id') }}</dt><dd><code>{{ detail.id }}</code><AppButton type="button" icon-only size="sm" variant="soft" :title="t('admin.tasks.copyId')" :aria-label="t('admin.tasks.copyId')" @click="copyId(detail.id, t('admin.tasks.id'))"><Copy :size="14" /></AppButton></dd></div>
        <div class="admin-copy-field"><dt>{{ t('admin.tasks.providerId') }}</dt><dd><code>{{ detail.provider_task_id || '—' }}</code><AppButton v-if="detail.provider_task_id" type="button" icon-only size="sm" variant="soft" :title="t('admin.tasks.copyProviderId')" :aria-label="t('admin.tasks.copyProviderId')" @click="copyId(detail.provider_task_id, t('admin.tasks.providerId'))"><Copy :size="14" /></AppButton></dd></div>
      </dl>
      <section v-if="detail.status === 'needs_review'" class="admin-provider-query">
        <AppButton size="sm" variant="soft" type="button" @click="openReview(detail)"><ClipboardCheck :size="14" />{{ t('admin.tasks.resolveReview') }}</AppButton>
        <p>{{ t('admin.tasks.reviewDescription') }}</p>
      </section>
      <section v-if="detail.provider === 'toapis' && detail.provider_task_id && ['image', 'video'].includes(detail.task_type)" class="admin-provider-query">
        <AppButton type="button" size="sm" variant="soft" :disabled="providerLoading" @click="refreshProviderStatus"><RefreshCw :size="14" :class="{ 'is-spinning': providerLoading }" />{{ t(providerLoading ? 'admin.tasks.querying' : 'admin.tasks.refreshProvider') }}</AppButton>
        <p v-if="providerState"><strong>{{ statusLabel(providerState.status) }}</strong> · {{ n(providerState.progress / 100, { style: 'percent' }) }}<span v-if="providerState.error_message"> · {{ providerState.error_message }}</span><small>{{ t('admin.tasks.checkedAt', { time: formatDate(providerState.checked_at) }) }}</small></p>
      </section>
      <details v-if="detail.diagnostic_snapshot || detail.error_message" class="admin-task-snapshot"><summary>{{ t('admin.tasks.rawError') }}</summary><p v-if="detail.error_message">{{ detail.error_message }}</p><pre v-if="detail.diagnostic_snapshot" class="admin-json">{{ formatSnapshot(detail.diagnostic_snapshot) }}</pre></details>
      <details class="admin-task-snapshot"><summary>{{ t('admin.tasks.requestSnapshot') }}</summary><pre class="admin-json">{{ formatSnapshot(detail.request_snapshot) }}</pre></details>
      <details class="admin-task-snapshot"><summary>{{ t('admin.tasks.pricingSnapshot') }}</summary><pre class="admin-json">{{ formatSnapshot(detail.pricing_snapshot) }}</pre></details>
      <details class="admin-task-snapshot"><summary>{{ t('admin.tasks.resultSnapshot') }}</summary><pre class="admin-json">{{ formatSnapshot(detail.result) }}</pre></details>
    </AdminDialog>
    <AdminDialog
      v-if="review.task"
      v-model:reason="review.reason"
      :title="t('admin.tasks.resolveReview')"
      :description="review.task.id"
      :confirm-text="t('admin.confirmSubmit')"
      :submitting="review.submitting"
      :danger="review.action !== 'resume'"
      @close="closeReview"
      @submit="resolveReview"
    >
      <div class="admin-form-grid">
        <label class="admin-field admin-field--wide">
          <span>{{ t('admin.tasks.reviewAction') }}</span>
          <AppSelect v-model="review.action" :options="reviewActionOptions" :aria-label="t('admin.tasks.reviewAction')" />
        </label>
        <label v-if="review.action === 'resume' && ['image', 'video'].includes(review.task.task_type)" class="admin-field admin-field--wide">
          <span>{{ t('admin.tasks.reviewProviderId') }}</span>
          <AppInput v-model.trim="review.providerTaskId" maxlength="128" :readonly="!!review.task.provider_task_id" :placeholder="t('admin.tasks.reviewProviderPlaceholder')" />
          <small>{{ t('admin.tasks.reviewProviderHint') }}</small>
        </label>
      </div>
      <p class="admin-dialog-note">{{ t(`admin.tasks.reviewNotes.${review.action}`) }}</p>
      <p v-if="review.action === 'resume' && review.task.task_type === 'audio'" class="admin-dialog-note">{{ t('admin.tasks.reviewAudioNote') }}</p>
    </AdminDialog>
  </section>
</template>
