<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Eye } from 'lucide-vue-next'
import { getAdminAudits } from '../../api/admin'
import AdminDialog from '../../components/admin/AdminDialog.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDateTime from '../../components/ui/AppDateTime.vue'
import AppInput from '../../components/ui/AppInput.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'

const toast = useGlobalToast()
const loading = ref(false)
const detail = ref(null)
const data = reactive({ items: [], page: 1, page_size: 20, total: 0 })
const filters = reactive({ admin_id: '', action: '', target_type: '', start_at: '', end_at: '' })
const columns = [
  { key: 'admin', label: '管理员' },
  { key: 'action', label: '操作' },
  { key: 'target', label: '目标' },
  { key: 'reason', label: '原因', class: 'admin-reason-cell' },
  { key: 'created_at', label: '时间' },
  { key: 'actions', label: '变更' },
]
async function load(page = 1) { loading.value = true; try { const params = { ...filters, page, page_size: data.page_size }; Object.keys(params).forEach((key) => params[key] === '' && delete params[key]); const result = await getAdminAudits(params); if (result.code !== 0) throw new Error(result.message); Object.assign(data, result.data) } catch (error) { toast.error(error.response?.data?.message || error.message || '审计记录加载失败') } finally { loading.value = false } }
function formatDate(value) { return new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) }
function pretty(value) { return JSON.stringify(value ?? {}, null, 2) }
onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>AUDIT TRAIL</span><h1>操作审计</h1><p>追踪后台写操作、原因及数据变更</p></div><b>{{ data.total }} 条记录</b></header>
    <form class="admin-filters admin-filters--wide" @submit.prevent="load(1)"><AppInput v-model="filters.admin_id" placeholder="管理员 ID" /><AppInput v-model="filters.action" placeholder="操作类型" /><AppInput v-model="filters.target_type" placeholder="目标类型" /><AppDateTime v-model="filters.start_at" aria-label="开始时间" placeholder="开始时间" /><AppDateTime v-model="filters.end_at" aria-label="结束时间" placeholder="结束时间" /><AppButton type="submit" variant="primary">查询</AppButton></form>
    <AppDataTable :columns="columns" :items="data.items" :loading="loading" loading-title="正在加载审计记录" empty-title="没有符合条件的审计记录" min-width="900px" :pagination="{ page: data.page, pageSize: data.page_size, total: data.total }" @page-change="load">
      <template #cell-admin="{ item: audit }"><strong>{{ audit.admin.username }}</strong><small>{{ audit.admin.id }}</small></template>
      <template #cell-target="{ item: audit }">{{ audit.target_type }}<small>{{ audit.target_id }}</small></template>
      <template #cell-created_at="{ value }">{{ formatDate(value) }}</template>
      <template #cell-actions="{ item: audit }"><AppButton size="sm" variant="soft" @click="detail = audit"><Eye :size="14" />查看</AppButton></template>
    </AppDataTable>
    <AdminDialog v-if="detail" title="变更详情" :description="detail.reason" :reason-required="false" confirm-text="关闭" @close="detail = null" @submit="detail = null"><div class="admin-snapshot-grid"><section><h3>变更前</h3><pre class="admin-json">{{ pretty(detail.before_snapshot) }}</pre></section><section><h3>变更后</h3><pre class="admin-json">{{ pretty(detail.after_snapshot) }}</pre></section></div></AdminDialog>
  </section>
</template>
