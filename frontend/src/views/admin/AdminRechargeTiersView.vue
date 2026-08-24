<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Pencil, Plus } from 'lucide-vue-next'
import { createAdminRechargeTier, getAdminBillingPolicy, getAdminRechargeTiers, updateAdminRechargeTier } from '../../api/admin'
import AdminDialog from '../../components/admin/AdminDialog.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { useAdminMutation } from '../../composables/useAdminMutation'
import { getApiErrorMessage } from '../../utils/apiError'

const toast = useGlobalToast()
const { confirmMutation } = useAdminMutation()
const loading = ref(false)
const tiers = ref([])
const policy = reactive({ unit_amount_cents: 3500, unit_credits: 1000 })
const dialog = reactive({ tier: null, open: false, reason: '', amount: '', bonus: '', enabled: 'true', submitting: false })
const enabledOptions = [{ value: 'true', label: '启用' }, { value: 'false', label: '停用' }]
const columns = [
  { key: 'min_amount_cents', label: '起充金额' },
  { key: 'bonus_rate_bps', label: '赠送比例' },
  { key: 'credits', label: '示例到账积分' },
  { key: 'enabled', label: '状态' },
  { key: 'updated_at', label: '更新时间' },
  { key: 'actions', label: '操作' },
]

async function load() {
  loading.value = true
  try {
    const [tierResult, policyResult] = await Promise.all([getAdminRechargeTiers(), getAdminBillingPolicy()])
    if (tierResult.code !== 0) throw new Error(tierResult.message)
    if (policyResult.code !== 0) throw new Error(policyResult.message)
    tiers.value = tierResult.data
    Object.assign(policy, policyResult.data)
  } catch (error) { toast.error(getApiErrorMessage(error, '充值阶梯加载失败')) }
  finally { loading.value = false }
}

function open(tier = null) {
  Object.assign(dialog, {
    tier, open: true, reason: '',
    amount: tier ? String(tier.min_amount_cents / 100) : '',
    bonus: tier ? String(tier.bonus_rate_bps / 100) : '',
    enabled: String(tier?.enabled ?? true),
  })
}

async function submit() {
  const payload = {
    reason: dialog.reason,
    min_amount_cents: Number(dialog.amount) * 100,
    bonus_rate_bps: Math.round(Number(dialog.bonus) * 100),
    enabled: dialog.enabled === 'true',
  }
  if (!await confirmMutation({ title: dialog.tier ? '更新充值阶梯' : '新增充值阶梯', message: `起充 ¥${dialog.amount}，赠送 ${dialog.bonus || 0}%` })) return
  dialog.submitting = true
  try {
    const result = dialog.tier ? await updateAdminRechargeTier(dialog.tier.id, payload) : await createAdminRechargeTier(payload)
    if (result.code !== 0) throw new Error(result.message)
    dialog.open = false
    toast.success('充值阶梯已保存')
    await load()
  } catch (error) { toast.error(getApiErrorMessage(error, '充值阶梯保存失败')) }
  finally { dialog.submitting = false }
}

function exampleCredits(tier) {
  const base = Math.floor(tier.min_amount_cents * policy.unit_credits / policy.unit_amount_cents)
  return base + Math.floor(base * tier.bonus_rate_bps / 10000)
}
function formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '—' }
onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>RECHARGE TIERS</span><h1>充值阶梯</h1><p>管理不同充值金额对应的赠送比例</p></div><b>{{ tiers.length }} 个阶梯</b></header>
    <div class="admin-toolbar"><p>金额越高，赠送比例不得降低，最高可设置 30%</p><AppButton variant="primary" @click="open()"><Plus :size="15" />新增阶梯</AppButton></div>
    <AppDataTable :columns="columns" :items="tiers" :loading="loading" loading-title="正在加载充值阶梯" empty-title="暂无充值阶梯" min-width="760px">
      <template #cell-min_amount_cents="{ value }"><strong>¥{{ value / 100 }}</strong></template>
      <template #cell-bonus_rate_bps="{ value }">{{ value / 100 }}%</template>
      <template #cell-credits="{ item }">{{ exampleCredits(item) }}</template>
      <template #cell-enabled="{ item }"><span class="admin-status" :class="item.enabled ? 'is-active' : 'is-disabled'">{{ item.enabled ? '启用' : '停用' }}</span></template>
      <template #cell-updated_at="{ value }">{{ formatDate(value) }}</template>
      <template #cell-actions="{ item }"><AppButton size="sm" variant="soft" @click="open(item)"><Pencil :size="14" />编辑</AppButton></template>
    </AppDataTable>
    <AdminDialog v-if="dialog.open" v-model:reason="dialog.reason" :title="dialog.tier ? '编辑充值阶梯' : '新增充值阶梯'" description="修改只影响后续创建的订单" :submitting="dialog.submitting" @close="dialog.open = false" @submit="submit"><div class="admin-form-grid"><label class="admin-field"><span>起充金额（元）</span><AppInput v-model="dialog.amount" type="number" min="1" max="100000" step="1" required /></label><label class="admin-field"><span>赠送比例（%）</span><AppInput v-model="dialog.bonus" type="number" min="0" max="30" step="0.01" required /></label><label class="admin-field"><span>状态</span><AppSelect v-model="dialog.enabled" :options="enabledOptions" aria-label="启用状态" /></label></div></AdminDialog>
  </section>
</template>
