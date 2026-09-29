<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDateTime } from '../../i18n'
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
const { t, n } = useI18n()
const { confirmMutation } = useAdminMutation()
const loading = ref(false)
const tiers = ref([])
const policy = reactive({ unit_amount_cents: 3500, unit_credits: 1000 })
const dialog = reactive({ tier: null, open: false, reason: '', amount: '', bonus: '', enabled: 'true', submitting: false })
const enabledOptions = computed(() => [{ value: 'true', label: t('admin.enabled') }, { value: 'false', label: t('admin.disabled') }])
const columns = computed(() => [
  { key: 'min_amount_cents', label: t('admin.tiers.minimum') },
  { key: 'bonus_rate_bps', label: t('admin.tiers.bonus') },
  { key: 'credits', label: t('admin.tiers.exampleCredits') },
  { key: 'enabled', label: t('admin.status') },
  { key: 'updated_at', label: t('common.updatedAt') },
  { key: 'actions', label: t('admin.actions') },
])

async function load() {
  loading.value = true
  try {
    const [tierResult, policyResult] = await Promise.all([getAdminRechargeTiers(), getAdminBillingPolicy()])
    if (tierResult.code !== 0) throw new Error(tierResult.message)
    if (policyResult.code !== 0) throw new Error(policyResult.message)
    tiers.value = tierResult.data
    Object.assign(policy, policyResult.data)
  } catch (error) { toast.error(getApiErrorMessage(error, t('admin.tiers.loadFailed'))) }
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
  if (!await confirmMutation({ title: t(dialog.tier ? 'admin.tiers.update' : 'admin.tiers.create'), message: t('admin.tiers.confirmation', { amount: n(Number(dialog.amount), { style: 'currency', currency: 'CNY' }), bonus: n(Number(dialog.bonus || 0) / 100, { style: 'percent', maximumFractionDigits: 2 }) }) })) return
  dialog.submitting = true
  try {
    const result = dialog.tier ? await updateAdminRechargeTier(dialog.tier.id, payload) : await createAdminRechargeTier(payload)
    if (result.code !== 0) throw new Error(result.message)
    dialog.open = false
    toast.success(t('admin.tiers.saved'))
    await load()
  } catch (error) { toast.error(getApiErrorMessage(error, t('admin.tiers.saveFailed'))) }
  finally { dialog.submitting = false }
}

function exampleCredits(tier) {
  const base = Math.floor(tier.min_amount_cents * policy.unit_credits / policy.unit_amount_cents)
  return base + Math.floor(base * tier.bonus_rate_bps / 10000)
}
function formatDate(value) { return value ? formatDateTime(value, { timeZone: 'Asia/Shanghai', dateStyle: 'short', timeStyle: 'medium' }) : '—' }
onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>{{ t('navigation.finance') }}</span><h1>{{ t('navigation.rechargeTiers') }}</h1><p>{{ t('admin.tiers.description') }}</p></div><b>{{ t('admin.tiers.count', { count: n(tiers.length) }) }}</b></header>
    <div class="admin-toolbar"><p>{{ t('admin.tiers.rule') }}</p><AppButton variant="primary" @click="open()"><Plus :size="15" />{{ t('admin.tiers.add') }}</AppButton></div>
    <AppDataTable :columns="columns" :items="tiers" :loading="loading" :loading-title="t('admin.tiers.loading')" :empty-title="t('admin.tiers.empty')" min-width="760px">
      <template #cell-min_amount_cents="{ value }"><strong>{{ n(value / 100, { style: 'currency', currency: 'CNY' }) }}</strong></template>
      <template #cell-bonus_rate_bps="{ value }">{{ n(value / 10000, { style: 'percent', maximumFractionDigits: 2 }) }}</template>
      <template #cell-credits="{ item }">{{ n(exampleCredits(item)) }}</template>
      <template #cell-enabled="{ item }"><span class="admin-status" :class="item.enabled ? 'is-active' : 'is-disabled'">{{ t(item.enabled ? 'admin.enabled' : 'admin.disabled') }}</span></template>
      <template #cell-updated_at="{ value }">{{ formatDate(value) }}</template>
      <template #cell-actions="{ item }"><AppButton size="sm" variant="soft" @click="open(item)"><Pencil :size="14" />{{ t('common.edit') }}</AppButton></template>
    </AppDataTable>
    <AdminDialog v-if="dialog.open" v-model:reason="dialog.reason" :title="t(dialog.tier ? 'admin.tiers.edit' : 'admin.tiers.create')" :description="t('admin.tiers.futureOrders')" :submitting="dialog.submitting" @close="dialog.open = false" @submit="submit"><div class="admin-form-grid"><label class="admin-field"><span>{{ t('admin.rechargePolicy.minimum') }}</span><AppInput v-model="dialog.amount" type="number" min="1" max="100000" step="1" required /></label><label class="admin-field"><span>{{ t('admin.tiers.bonusPercent') }}</span><AppInput v-model="dialog.bonus" type="number" min="0" max="30" step="0.01" required /></label><label class="admin-field"><span>{{ t('admin.status') }}</span><AppSelect v-model="dialog.enabled" :options="enabledOptions" :aria-label="t('admin.models.enabledStatus')" /></label></div></AdminDialog>
  </section>
</template>
