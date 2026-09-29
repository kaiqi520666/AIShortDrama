<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Pencil } from 'lucide-vue-next'
import { getAdminModels, updateAdminModel } from '../../api/admin'
import AdminDialog from '../../components/admin/AdminDialog.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppDataTable from '../../components/ui/AppDataTable.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import { useAdminMutation } from '../../composables/useAdminMutation'
import { useGlobalToast } from '../../composables/useGlobalUI'
import { getApiErrorMessage } from '../../utils/apiError'

const toast = useGlobalToast()
const { t, n } = useI18n()
const { confirmMutation } = useAdminMutation()
const loading = ref(false)
const models = ref([])
const dialog = reactive({ item: null, label: '', enabled: 'true', isDefault: 'false', reason: '', submitting: false })
const mediaTypes = computed(() => ['text', 'image', 'video', 'audio'].map((key) => ({ key, label: t(`home.${key}`) })))
const enabledOptions = computed(() => [{ value: 'true', label: t('admin.enabled') }, { value: 'false', label: t('admin.disabled') }])
const defaultOptions = computed(() => [{ value: 'true', label: t('admin.models.defaultOption') }, { value: 'false', label: t('admin.models.notDefault') }])
const columns = computed(() => [
  { key: 'label', label: t('admin.models.label') },
  { key: 'model_id', label: t('admin.models.id') },
  { key: 'enabled', label: t('admin.status') },
  { key: 'is_default', label: t('admin.default') },
  { key: 'actions', label: t('admin.actions'), align: 'right' },
])
const groupedModels = computed(() => Object.fromEntries(mediaTypes.value.map(({ key }) => [key, models.value.filter((item) => item.media_type === key)])))

async function load() {
  loading.value = true
  try {
    const result = await getAdminModels()
    if (result.code !== 0) throw new Error(result.message)
    models.value = result.data
  } catch (error) {
    toast.error(getApiErrorMessage(error, t('admin.models.loadFailed')))
  } finally {
    loading.value = false
  }
}

function open(item) {
  Object.assign(dialog, {
    item,
    label: item.label,
    enabled: String(item.enabled),
    isDefault: String(item.is_default),
    reason: '',
    submitting: false,
  })
}

function close() {
  if (!dialog.submitting) dialog.item = null
}

async function submit() {
  const payload = {
    label: dialog.label.trim(),
    enabled: dialog.enabled === 'true',
    is_default: dialog.isDefault === 'true',
    reason: dialog.reason,
  }
  if (!await confirmMutation({
    title: t('admin.models.update'),
    message: t('admin.models.updateMessage', { label: dialog.item.label, id: dialog.item.model_id, status: t(payload.enabled ? 'admin.enabled' : 'admin.disabled'), defaultText: payload.is_default ? t('admin.models.setDefaultSuffix') : '' }),
  })) return
  dialog.submitting = true
  try {
    const result = await updateAdminModel(dialog.item.media_type, dialog.item.model_id, payload)
    if (result.code !== 0) throw new Error(result.message)
    toast.success(t('admin.models.updated'))
    dialog.item = null
    await load()
  } catch (error) {
    toast.error(getApiErrorMessage(error, t('admin.models.saveFailed')))
  } finally {
    dialog.submitting = false
  }
}

onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>{{ t('navigation.content') }}</span><h1>{{ t('navigation.models') }}</h1><p>{{ t('admin.models.description') }}</p></div><b>{{ t('admin.models.count', { count: n(models.length) }) }}</b></header>
    <section v-for="media in mediaTypes" :key="media.key" class="admin-model-group">
      <header><h2>{{ t('admin.models.group', { type: media.label }) }}</h2><small>{{ t('admin.models.count', { count: n(groupedModels[media.key].length) }) }}</small></header>
      <AppDataTable :columns="columns" :items="groupedModels[media.key]" :loading="loading" :loading-title="t('admin.models.loading')" :empty-title="t('admin.models.empty')" min-width="760px">
        <template #cell-label="{ item }"><strong>{{ item.label }}</strong></template>
        <template #cell-model_id="{ value }"><code>{{ value }}</code></template>
        <template #cell-enabled="{ item }"><span class="admin-status" :class="item.enabled ? 'is-active' : 'is-disabled'">{{ t(item.enabled ? 'admin.enabled' : 'admin.disabled') }}</span></template>
        <template #cell-is_default="{ item }"><span class="admin-badge" :class="{ 'is-admin': item.is_default }">{{ item.is_default ? t('admin.default') : '—' }}</span></template>
        <template #cell-actions="{ item }"><AppButton size="sm" variant="soft" @click="open(item)"><Pencil :size="14" />{{ t('common.edit') }}</AppButton></template>
      </AppDataTable>
    </section>

    <AdminDialog v-if="dialog.item" v-model:reason="dialog.reason" :title="t('admin.models.edit')" :description="`${dialog.item.media_type} · ${dialog.item.model_id}`" :submitting="dialog.submitting" @close="close" @submit="submit">
      <div class="admin-form-grid">
        <label class="admin-field"><span>{{ t('admin.models.label') }}</span><AppInput v-model="dialog.label" maxlength="100" required /></label>
        <label class="admin-field"><span>{{ t('admin.models.enabledStatus') }}</span><AppSelect v-model="dialog.enabled" :options="enabledOptions" :aria-label="t('admin.models.enabledAria')" /></label>
        <label class="admin-field admin-field--wide"><span>{{ t('admin.models.defaultModel') }}</span><AppSelect v-model="dialog.isDefault" :options="defaultOptions" :aria-label="t('admin.models.defaultAria')" /></label>
      </div>
    </AdminDialog>
  </section>
</template>
