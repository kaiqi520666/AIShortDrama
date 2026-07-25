<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Eye, Search } from 'lucide-vue-next'
import { getAdminTasks } from '../../api/admin'
import AdminDialog from '../../components/admin/AdminDialog.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDateTime from '../../components/ui/AppDateTime.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'

const toast = useGlobalToast()
const loading = ref(false)
const detail = ref(null)
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
async function load(page = 1) { loading.value = true; try { const params = { ...filters, page, page_size: data.page_size }; if (!params.start_at) delete params.start_at; if (!params.end_at) delete params.end_at; const result = await getAdminTasks(params); if (result.code !== 0) throw new Error(result.message); Object.assign(data, result.data) } catch (error) { toast.error(error.response?.data?.message || error.message || '任务加载失败') } finally { loading.value = false } }
function formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '—' }
function pretty(value) { return JSON.stringify(value ?? {}, null, 2) }
onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>GENERATION MONITOR</span><h1>生成任务</h1><p>查询全部生成任务与计费快照</p></div><b>{{ data.total }} 个任务</b></header>
    <form class="admin-filters admin-filters--wide" @submit.prevent="load(1)"><label class="admin-search"><Search :size="15" /><AppInput v-model="filters.q" placeholder="用户名或邮箱" /></label><AppSelect v-model="filters.media_type" :options="mediaOptions" aria-label="任务类型" /><AppInput v-model="filters.model" placeholder="模型名称" /><AppInput v-model="filters.status" placeholder="任务状态" /><AppDateTime v-model="filters.start_at" aria-label="开始时间" placeholder="开始时间" /><AppDateTime v-model="filters.end_at" aria-label="结束时间" placeholder="结束时间" /><AppButton type="submit" variant="primary">查询</AppButton></form>
    <AppDataTable :columns="columns" :items="data.items" :loading="loading" loading-title="正在加载生成任务" empty-title="没有符合条件的任务" min-width="900px" :pagination="{ page: data.page, pageSize: data.page_size, total: data.total }" @page-change="load">
      <template #cell-user="{ item: task }"><strong>{{ task.user.username }}</strong><small>{{ task.user.email }}</small></template>
      <template #cell-status="{ item: task }"><span class="admin-status" :class="`is-${task.status}`">{{ task.status }}</span></template>
      <template #cell-credits="{ item: task }">{{ task.charged_credits }} / {{ task.frozen_credits }}</template>
      <template #cell-created_at="{ value }">{{ formatDate(value) }}</template>
      <template #cell-actions="{ item: task }"><AppButton size="sm" variant="soft" @click="detail = task"><Eye :size="14" />查看</AppButton></template>
    </AppDataTable>
    <AdminDialog v-if="detail" title="任务详情" :description="detail.id" :reason-required="false" confirm-text="关闭" @close="detail = null" @submit="detail = null"><dl class="admin-detail-list"><div><dt>状态</dt><dd>{{ detail.status }} · {{ detail.progress }}%</dd></div><div><dt>错误</dt><dd>{{ detail.error_message || '—' }}</dd></div></dl><h3 class="admin-detail-title">请求快照</h3><pre class="admin-json">{{ pretty(detail.request_snapshot) }}</pre><h3 class="admin-detail-title">计费快照</h3><pre class="admin-json">{{ pretty(detail.pricing_snapshot) }}</pre><h3 class="admin-detail-title">结果快照</h3><pre class="admin-json">{{ pretty(detail.result) }}</pre></AdminDialog>
  </section>
</template>
