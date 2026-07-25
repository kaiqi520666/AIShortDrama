<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Coins, KeyRound, Search, ShieldCheck, UserCog } from 'lucide-vue-next'
import { adjustUserCredits, getAdminUsers, resetUserPassword, updateUserRole, updateUserStatus } from '../../api/admin'
import AdminDialog from '../../components/admin/AdminDialog.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'

const toast = useGlobalToast()
const loading = ref(false)
const data = reactive({ items: [], page: 1, page_size: 20, total: 0 })
const filters = reactive({ q: '', status: 'all', role: 'all' })
const dialog = reactive({ type: '', user: null, reason: '', value: '', submitting: false })
const statusOptions = [{ value: 'all', label: '全部状态' }, { value: 'active', label: '启用' }, { value: 'disabled', label: '停用' }]
const roleOptions = [{ value: 'all', label: '全部角色' }, { value: 'user', label: '普通用户' }, { value: 'admin', label: '管理员' }]
const columns = [
  { key: 'user', label: '用户' },
  { key: 'role', label: '角色' },
  { key: 'status', label: '状态' },
  { key: 'credit_balance', label: '可用积分' },
  { key: 'credit_frozen', label: '冻结积分' },
  { key: 'created_at', label: '注册时间' },
  { key: 'actions', label: '操作', align: 'right' },
]

async function load(page = 1) {
  loading.value = true
  try {
    const result = await getAdminUsers({ ...filters, page, page_size: data.page_size })
    if (result.code !== 0) throw new Error(result.message)
    Object.assign(data, result.data)
  } catch (error) { toast.error(error.response?.data?.message || error.message || '用户加载失败') }
  finally { loading.value = false }
}

function open(type, user) {
  Object.assign(dialog, { type, user, reason: '', value: type === 'role' ? user.role : type === 'status' ? (user.status === 'active' ? 'disabled' : 'active') : '', submitting: false })
}
function close() { if (!dialog.submitting) dialog.type = '' }
function title() { return ({ credits: '调整积分', role: '修改角色', status: dialog.value === 'disabled' ? '停用用户' : '启用用户', password: '重置密码' })[dialog.type] }

async function submit() {
  dialog.submitting = true
  try {
    const payload = { reason: dialog.reason }
    if (dialog.type === 'credits') await adjustUserCredits(dialog.user.id, { ...payload, amount: Number(dialog.value) })
    else if (dialog.type === 'role') await updateUserRole(dialog.user.id, { ...payload, role: dialog.value })
    else if (dialog.type === 'status') await updateUserStatus(dialog.user.id, { ...payload, status: dialog.value })
    else await resetUserPassword(dialog.user.id, { ...payload, new_password: dialog.value })
    toast.success('操作已完成')
    dialog.type = ''
    await load(data.page)
  } catch (error) { toast.error(error.response?.data?.message || error.message || '操作失败') }
  finally { dialog.submitting = false }
}

function formatDate(value) { return new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) }
onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>ADMINISTRATION</span><h1>用户管理</h1><p>查询账号、调整积分与管理访问权限</p></div><b>{{ data.total }} 位用户</b></header>
    <form class="admin-filters" @submit.prevent="load(1)"><label class="admin-search"><Search :size="15" /><AppInput v-model="filters.q" placeholder="搜索用户名或邮箱" /></label><AppSelect v-model="filters.status" :options="statusOptions" aria-label="用户状态" /><AppSelect v-model="filters.role" :options="roleOptions" aria-label="用户角色" /><AppButton type="submit" variant="primary">查询</AppButton></form>
    <AppDataTable
      :columns="columns"
      :items="data.items"
      :loading="loading"
      loading-title="正在加载用户"
      empty-title="没有符合条件的用户"
      min-width="900px"
      :pagination="{ page: data.page, pageSize: data.page_size, total: data.total }"
      @page-change="load"
    >
      <template #cell-user="{ item: user }"><strong>{{ user.username }}</strong><small>{{ user.email }}</small></template>
      <template #cell-role="{ item: user }"><span class="admin-badge" :class="`is-${user.role}`">{{ user.role === 'admin' ? '管理员' : '普通用户' }}</span></template>
      <template #cell-status="{ item: user }"><span class="admin-status" :class="`is-${user.status}`">{{ user.status === 'active' ? '启用' : '停用' }}</span></template>
      <template #cell-created_at="{ value }">{{ formatDate(value) }}</template>
      <template #cell-actions="{ item: user }">
        <div class="admin-table-actions">
          <AppButton size="sm" variant="soft" title="调整积分" @click="open('credits', user)"><Coins :size="14" /></AppButton>
          <AppButton size="sm" variant="soft" title="修改角色" @click="open('role', user)"><ShieldCheck :size="14" /></AppButton>
          <AppButton size="sm" variant="soft" title="重置密码" @click="open('password', user)"><KeyRound :size="14" /></AppButton>
          <AppButton size="sm" :variant="user.status === 'active' ? 'danger' : 'soft'" :title="user.status === 'active' ? '停用' : '启用'" @click="open('status', user)"><UserCog :size="14" /></AppButton>
        </div>
      </template>
    </AppDataTable>
    <AdminDialog v-if="dialog.type" v-model:reason="dialog.reason" :title="title()" :description="`${dialog.user.username} · ${dialog.user.email}`" :submitting="dialog.submitting" :danger="dialog.type === 'status' && dialog.value === 'disabled'" @close="close" @submit="submit">
      <label v-if="dialog.type === 'credits'" class="admin-field"><span>积分变动</span><AppInput v-model="dialog.value" type="number" min="-1000000" max="1000000" required placeholder="正数增加，负数扣减" /></label>
      <label v-else-if="dialog.type === 'role'" class="admin-field"><span>角色</span><AppSelect v-model="dialog.value" :options="roleOptions.slice(1)" aria-label="目标角色" /></label>
      <label v-else-if="dialog.type === 'password'" class="admin-field"><span>新密码</span><AppInput v-model="dialog.value" type="password" minlength="8" maxlength="72" autocomplete="new-password" required /></label>
      <p v-else class="admin-dialog-note">该用户将{{ dialog.value === 'disabled' ? '立即退出所有设备并无法登录' : '恢复登录和使用权限' }}。</p>
    </AdminDialog>
  </section>
</template>
