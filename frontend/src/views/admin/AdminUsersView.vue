<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDateTime } from '../../i18n'
import { Coins, KeyRound, Search, ShieldCheck, UserCog } from 'lucide-vue-next'
import { adjustUserCredits, getAdminUsers, resetUserPassword, updateUserRole, updateUserStatus } from '../../api/admin'
import AdminDialog from '../../components/admin/AdminDialog.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { useAdminMutation } from '../../composables/useAdminMutation'
import { getApiErrorMessage } from '../../utils/apiError'

const toast = useGlobalToast()
const { t, n } = useI18n()
const { confirmMutation } = useAdminMutation()
const loading = ref(false)
const data = reactive({ items: [], page: 1, page_size: 20, total: 0 })
const filters = reactive({ q: '', status: 'all', role: 'all' })
const dialog = reactive({ type: '', user: null, reason: '', value: '', submitting: false })
const statusOptions = computed(() => [{ value: 'all', label: t('admin.allStatuses') }, { value: 'active', label: t('admin.enabled') }, { value: 'disabled', label: t('admin.disabled') }])
const roleOptions = computed(() => [{ value: 'all', label: t('admin.users.allRoles') }, { value: 'user', label: t('admin.users.user') }, { value: 'admin', label: t('admin.users.admin') }])
const columns = computed(() => [
  { key: 'user', label: t('common.user') },
  { key: 'role', label: t('admin.users.role') },
  { key: 'status', label: t('admin.status') },
  { key: 'credit_balance', label: t('account.available') },
  { key: 'credit_frozen', label: t('account.frozen') },
  { key: 'created_at', label: t('account.registered') },
  { key: 'actions', label: t('admin.actions'), align: 'right' },
])

async function load(page = 1) {
  loading.value = true
  try {
    const result = await getAdminUsers({ ...filters, page, page_size: data.page_size })
    if (result.code !== 0) throw new Error(result.message)
    Object.assign(data, result.data)
  } catch (error) { toast.error(getApiErrorMessage(error, t('admin.users.loadFailed'))) }
  finally { loading.value = false }
}

function open(type, user) {
  Object.assign(dialog, { type, user, reason: '', value: type === 'role' ? user.role : type === 'status' ? (user.status === 'active' ? 'disabled' : 'active') : '', submitting: false })
}
function close() { if (!dialog.submitting) dialog.type = '' }
function title() { return t(`admin.users.${({ credits: 'credits', role: 'changeRole', status: dialog.value === 'disabled' ? 'disable' : 'enable', password: 'resetPassword' })[dialog.type]}`) }

async function submit() {
  const mutation = {
    type: dialog.type,
    user: dialog.user,
    reason: dialog.reason,
    value: dialog.value,
    title: title(),
  }
  if (!await confirmMutation({
    title: mutation.title,
    message: `${mutation.user.username} · ${mutation.user.email}`,
  })) return
  dialog.submitting = true
  try {
    const payload = { reason: mutation.reason }
    if (mutation.type === 'credits') await adjustUserCredits(mutation.user.id, { ...payload, amount: Number(mutation.value) })
    else if (mutation.type === 'role') await updateUserRole(mutation.user.id, { ...payload, role: mutation.value })
    else if (mutation.type === 'status') await updateUserStatus(mutation.user.id, { ...payload, status: mutation.value })
    else if (mutation.type === 'password') await resetUserPassword(mutation.user.id, { ...payload, new_password: mutation.value })
    toast.success(t('admin.completed'))
    dialog.type = ''
    await load(data.page)
  } catch (error) { toast.error(getApiErrorMessage(error, t('common.operationFailed'))) }
  finally { dialog.submitting = false }
}

function formatDate(value) { return formatDateTime(value, { timeZone: 'Asia/Shanghai', dateStyle: 'short', timeStyle: 'medium' }) }
onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>{{ t('navigation.admin') }}</span><h1>{{ t('navigation.users') }}</h1><p>{{ t('admin.users.description') }}</p></div><b>{{ t('admin.users.count', { count: n(data.total) }) }}</b></header>
    <form class="admin-filters" @submit.prevent="load(1)"><label class="admin-search"><Search :size="15" /><AppInput v-model="filters.q" :placeholder="t('admin.users.search')" /></label><AppSelect v-model="filters.status" :options="statusOptions" :aria-label="t('admin.users.userStatus')" /><AppSelect v-model="filters.role" :options="roleOptions" :aria-label="t('admin.users.userRole')" /><AppButton type="submit" variant="primary">{{ t('admin.query') }}</AppButton></form>
    <AppDataTable
      :columns="columns"
      :items="data.items"
      :loading="loading"
      :loading-title="t('admin.users.loading')"
      :empty-title="t('admin.users.empty')"
      min-width="900px"
      :pagination="{ page: data.page, pageSize: data.page_size, total: data.total }"
      @page-change="load"
    >
      <template #cell-user="{ item: user }"><strong>{{ user.username }}</strong><small>{{ user.email }}</small></template>
      <template #cell-role="{ item: user }"><span class="admin-badge" :class="`is-${user.role}`">{{ t(user.role === 'admin' ? 'admin.users.admin' : 'admin.users.user') }}</span></template>
      <template #cell-status="{ item: user }"><span class="admin-status" :class="`is-${user.status}`">{{ t(user.status === 'active' ? 'admin.enabled' : 'admin.disabled') }}</span></template>
      <template #cell-credit_balance="{ value }">{{ n(value) }}</template>
      <template #cell-credit_frozen="{ value }">{{ n(value) }}</template>
      <template #cell-created_at="{ value }">{{ formatDate(value) }}</template>
      <template #cell-actions="{ item: user }">
        <div class="admin-table-actions">
          <AppButton size="sm" variant="soft" :title="t('admin.users.credits')" @click="open('credits', user)"><Coins :size="14" /></AppButton>
          <AppButton size="sm" variant="soft" :title="t('admin.users.changeRole')" @click="open('role', user)"><ShieldCheck :size="14" /></AppButton>
          <AppButton size="sm" variant="soft" :title="t('admin.users.resetPassword')" @click="open('password', user)"><KeyRound :size="14" /></AppButton>
          <AppButton size="sm" :variant="user.status === 'active' ? 'danger' : 'soft'" :title="t(user.status === 'active' ? 'admin.disabled' : 'admin.enabled')" @click="open('status', user)"><UserCog :size="14" /></AppButton>
        </div>
      </template>
    </AppDataTable>
    <AdminDialog v-if="dialog.type" v-model:reason="dialog.reason" :title="title()" :description="`${dialog.user.username} · ${dialog.user.email}`" :submitting="dialog.submitting" :danger="dialog.type === 'status' && dialog.value === 'disabled'" @close="close" @submit="submit">
      <label v-if="dialog.type === 'credits'" class="admin-field"><span>{{ t('admin.users.creditChange') }}</span><AppInput v-model="dialog.value" type="number" min="-1000000" max="1000000" required :placeholder="t('admin.users.creditPlaceholder')" /></label>
      <label v-else-if="dialog.type === 'role'" class="admin-field"><span>{{ t('admin.users.role') }}</span><AppSelect v-model="dialog.value" :options="roleOptions.slice(1)" :aria-label="t('admin.users.targetRole')" /></label>
      <label v-else-if="dialog.type === 'password'" class="admin-field"><span>{{ t('account.newPassword') }}</span><AppInput v-model="dialog.value" type="password" minlength="8" maxlength="72" autocomplete="new-password" required /></label>
      <p v-else class="admin-dialog-note">{{ t(dialog.value === 'disabled' ? 'admin.users.disableNote' : 'admin.users.enableNote') }}</p>
    </AdminDialog>
  </section>
</template>
