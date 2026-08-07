<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
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
const { confirmMutation } = useAdminMutation()
const loading = ref(false)
const models = ref([])
const dialog = reactive({ item: null, label: '', enabled: 'true', isDefault: 'false', reason: '', submitting: false })
const mediaTypes = [
  { key: 'text', label: '文本' },
  { key: 'image', label: '图片' },
  { key: 'video', label: '视频' },
  { key: 'audio', label: '音频' },
]
const enabledOptions = [{ value: 'true', label: '启用' }, { value: 'false', label: '停用' }]
const defaultOptions = [{ value: 'true', label: '设为默认模型' }, { value: 'false', label: '非默认模型' }]
const columns = [
  { key: 'label', label: '展示名称' },
  { key: 'model_id', label: '模型 ID' },
  { key: 'enabled', label: '状态' },
  { key: 'is_default', label: '默认' },
  { key: 'actions', label: '操作', align: 'right' },
]
const groupedModels = computed(() => Object.fromEntries(mediaTypes.map(({ key }) => [key, models.value.filter((item) => item.media_type === key)])))

async function load() {
  loading.value = true
  try {
    const result = await getAdminModels()
    if (result.code !== 0) throw new Error(result.message)
    models.value = result.data
  } catch (error) {
    toast.error(getApiErrorMessage(error, '模型配置加载失败'))
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
    title: '更新模型配置',
    message: `${dialog.item.label}（${dialog.item.model_id}）将${payload.enabled ? '启用' : '停用'}${payload.is_default ? '并设为默认模型' : ''}。`,
  })) return
  dialog.submitting = true
  try {
    const result = await updateAdminModel(dialog.item.media_type, dialog.item.model_id, payload)
    if (result.code !== 0) throw new Error(result.message)
    toast.success('模型配置已更新')
    dialog.item = null
    await load()
  } catch (error) {
    toast.error(getApiErrorMessage(error, '模型配置保存失败'))
  } finally {
    dialog.submitting = false
  }
}

onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>MODEL CONTROL</span><h1>模型管理</h1><p>控制模型展示、可用状态和默认模型，不开放能力边界或 Provider 参数</p></div><b>{{ models.length }} 个模型</b></header>
    <section v-for="media in mediaTypes" :key="media.key" class="admin-model-group">
      <header><h2>{{ media.label }}模型</h2><small>{{ groupedModels[media.key].length }} 个</small></header>
      <AppDataTable :columns="columns" :items="groupedModels[media.key]" :loading="loading" loading-title="正在加载模型配置" empty-title="暂无模型配置" min-width="760px">
        <template #cell-label="{ item }"><strong>{{ item.label }}</strong></template>
        <template #cell-model_id="{ value }"><code>{{ value }}</code></template>
        <template #cell-enabled="{ item }"><span class="admin-status" :class="item.enabled ? 'is-active' : 'is-disabled'">{{ item.enabled ? '启用' : '停用' }}</span></template>
        <template #cell-is_default="{ item }"><span class="admin-badge" :class="{ 'is-admin': item.is_default }">{{ item.is_default ? '默认' : '—' }}</span></template>
        <template #cell-actions="{ item }"><AppButton size="sm" variant="soft" @click="open(item)"><Pencil :size="14" />编辑</AppButton></template>
      </AppDataTable>
    </section>

    <AdminDialog v-if="dialog.item" v-model:reason="dialog.reason" title="编辑模型配置" :description="`${dialog.item.media_type} · ${dialog.item.model_id}`" :submitting="dialog.submitting" @close="close" @submit="submit">
      <div class="admin-form-grid">
        <label class="admin-field"><span>展示名称</span><AppInput v-model="dialog.label" maxlength="100" required /></label>
        <label class="admin-field"><span>启用状态</span><AppSelect v-model="dialog.enabled" :options="enabledOptions" aria-label="模型启用状态" /></label>
        <label class="admin-field admin-field--wide"><span>默认模型</span><AppSelect v-model="dialog.isDefault" :options="defaultOptions" aria-label="默认模型状态" /></label>
      </div>
    </AdminDialog>
  </section>
</template>
