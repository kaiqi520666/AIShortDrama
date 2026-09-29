<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDateTime } from '../../i18n'
import { Eye } from 'lucide-vue-next'
import { getAdminAudits } from '../../api/admin'
import AdminDialog from '../../components/admin/AdminDialog.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppDateTime from '../../components/ui/AppDateTime.vue'
import AppInput from '../../components/ui/AppInput.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { getApiErrorMessage } from '../../utils/apiError'

const toast = useGlobalToast()
const { t, n } = useI18n()
const loading = ref(false)
const detail = ref(null)
const data = reactive({ items: [], page: 1, page_size: 20, total: 0 })
const filters = reactive({ admin_id: '', action: '', target_type: '', start_at: '', end_at: '' })
const columns = computed(() => [
  { key: 'admin', label: t('admin.users.admin') },
  { key: 'action', label: t('admin.actions') },
  { key: 'target', label: t('admin.audits.target') },
  { key: 'reason', label: t('admin.audits.reason'), class: 'admin-reason-cell' },
  { key: 'created_at', label: t('admin.audits.time') },
  { key: 'actions', label: t('admin.audits.changes') },
])
async function load(page = 1) { loading.value = true; try { const params = { ...filters, page, page_size: data.page_size }; Object.keys(params).forEach((key) => params[key] === '' && delete params[key]); const result = await getAdminAudits(params); if (result.code !== 0) throw new Error(result.message); Object.assign(data, result.data) } catch (error) { toast.error(getApiErrorMessage(error, t('admin.audits.loadFailed'))) } finally { loading.value = false } }
function formatDate(value) { return formatDateTime(value, { timeZone: 'Asia/Shanghai', dateStyle: 'short', timeStyle: 'medium' }) }
function pretty(value) { return JSON.stringify(value ?? {}, null, 2) }
onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>{{ t('navigation.operations') }}</span><h1>{{ t('navigation.audits') }}</h1><p>{{ t('admin.audits.description') }}</p></div><b>{{ t('common.totalRecords', { count: n(data.total) }) }}</b></header>
    <form class="admin-filters admin-filters--wide" @submit.prevent="load(1)"><AppInput v-model="filters.admin_id" :placeholder="t('admin.audits.adminId')" /><AppInput v-model="filters.action" :placeholder="t('admin.audits.actionType')" /><AppInput v-model="filters.target_type" :placeholder="t('admin.audits.targetType')" /><AppDateTime v-model="filters.start_at" :aria-label="t('common.startTime')" :placeholder="t('common.startTime')" /><AppDateTime v-model="filters.end_at" :aria-label="t('common.endTime')" :placeholder="t('common.endTime')" /><AppButton type="submit" variant="primary">{{ t('admin.query') }}</AppButton></form>
    <AppDataTable :columns="columns" :items="data.items" :loading="loading" :loading-title="t('admin.audits.loading')" :empty-title="t('admin.audits.empty')" min-width="900px" :pagination="{ page: data.page, pageSize: data.page_size, total: data.total }" @page-change="load">
      <template #cell-admin="{ item: audit }"><strong>{{ audit.admin.username }}</strong><small>{{ audit.admin.id }}</small></template>
      <template #cell-target="{ item: audit }">{{ audit.target_type }}<small>{{ audit.target_id }}</small></template>
      <template #cell-created_at="{ value }">{{ formatDate(value) }}</template>
      <template #cell-actions="{ item: audit }"><AppButton size="sm" variant="soft" @click="detail = audit"><Eye :size="14" />{{ t('common.view') }}</AppButton></template>
    </AppDataTable>
    <AdminDialog v-if="detail" :title="t('admin.audits.detail')" :description="detail.reason" :reason-required="false" :confirm-text="t('common.close')" @close="detail = null" @submit="detail = null"><div class="admin-snapshot-grid"><section><h3>{{ t('admin.audits.before') }}</h3><pre class="admin-json">{{ pretty(detail.before_snapshot) }}</pre></section><section><h3>{{ t('admin.audits.after') }}</h3><pre class="admin-json">{{ pretty(detail.after_snapshot) }}</pre></section></div></AdminDialog>
  </section>
</template>
