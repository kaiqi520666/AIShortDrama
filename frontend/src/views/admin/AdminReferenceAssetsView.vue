<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Pencil, Plus, RefreshCw, Search, Upload } from 'lucide-vue-next'
import { createAdminReferenceAsset, getAdminReferenceAssets, registerAdminSystemCharacter, updateAdminReferenceAsset } from '../../api/admin'
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
const items = ref([])
const filters = reactive({ resource_type: 'all', active: 'all' })
const dialog = reactive({ type: '', asset: null, file: null, name: '', sortOrder: '0', active: 'true', tags: '', copyrightNote: '', reason: '', submitting: false })
const resourceOptions = computed(() => ['all', 'model', 'character', 'garment'].map((value) => ({ value, label: t(`admin.assets.${value}`) })))
const editableResourceOptions = computed(() => resourceOptions.value.slice(1))
const activeOptions = computed(() => [{ value: 'all', label: t('admin.allStatuses') }, { value: 'active', label: t('admin.assets.listed') }, { value: 'inactive', label: t('admin.assets.unlisted') }])
const enabledOptions = computed(() => [{ value: 'true', label: t('admin.assets.list') }, { value: 'false', label: t('admin.assets.unlist') }])
const columns = computed(() => [
  { key: 'preview', label: t('admin.assets.asset') },
  { key: 'resource_type', label: t('admin.tasks.type') },
  { key: 'library', label: t('admin.assets.tags') },
  { key: 'sort_order', label: t('admin.assets.sort') },
  { key: 'active', label: t('admin.status') },
  { key: 'seedance', label: t('admin.assets.avatar') },
  { key: 'actions', label: t('admin.actions'), align: 'right' },
])
const resourceLabel = computed(() => Object.fromEntries(resourceOptions.value.map((item) => [item.value, item.label])))
const filteredItems = computed(() => items.value)

async function load() {
  loading.value = true
  try {
    const result = await getAdminReferenceAssets({ ...filters })
    if (result.code !== 0) throw new Error(result.message)
    items.value = result.data
  } catch (error) {
    toast.error(getApiErrorMessage(error, t('admin.assets.loadFailed')))
  } finally {
    loading.value = false
  }
}

function resetDialog() {
  Object.assign(dialog, { type: '', asset: null, file: null, name: '', sortOrder: '0', active: 'true', tags: '', copyrightNote: '', reason: '', submitting: false })
}

function openCreate() {
  resetDialog()
  dialog.type = 'create'
  dialog.resourceType = 'model'
}

function openEdit(asset) {
  resetDialog()
  Object.assign(dialog, {
    type: 'edit',
    asset,
    name: asset.name,
    sortOrder: String(asset.sort_order),
    active: String(asset.active),
    tags: (asset.library?.tags || []).join(', '),
    copyrightNote: asset.library?.copyright_note || '',
  })
}

function openRegister(asset) {
  resetDialog()
  dialog.type = 'register'
  dialog.asset = asset
}

function fileChanged(event) {
  dialog.file = event.target.files?.[0] || null
}

function tagValues() {
  return dialog.tags.split(',').map((value) => value.trim()).filter(Boolean)
}

async function submit() {
  const action = t(dialog.type === 'create' ? 'admin.assets.upload' : dialog.type === 'edit' ? 'admin.assets.update' : 'admin.assets.retry')
  if (dialog.type === 'create' && !dialog.file) {
    toast.error(t('admin.assets.selectFile'))
    return
  }
  if (!await confirmMutation({
    title: action,
    message: t(dialog.type === 'register' ? 'admin.assets.registerConfirmation' : 'admin.assets.updateConfirmation', { name: dialog.type === 'register' ? dialog.asset.name : dialog.name }),
  })) return
  dialog.submitting = true
  try {
    let result
    if (dialog.type === 'create') {
      const formData = new FormData()
      formData.set('resource_type', dialog.resourceType)
      formData.set('file', dialog.file)
      formData.set('name', dialog.name)
      formData.set('sort_order', dialog.sortOrder)
      formData.set('tags', dialog.tags)
      formData.set('copyright_note', dialog.copyrightNote)
      formData.set('reason', dialog.reason)
      result = await createAdminReferenceAsset(formData)
    } else if (dialog.type === 'edit') {
      result = await updateAdminReferenceAsset(dialog.asset.resource_type, dialog.asset.id, {
        name: dialog.name,
        sort_order: Number(dialog.sortOrder),
        active: dialog.active === 'true',
        tags: tagValues(),
        copyright_note: dialog.copyrightNote,
        reason: dialog.reason,
      })
    } else {
      const formData = new FormData()
      formData.set('reason', dialog.reason)
      result = await registerAdminSystemCharacter(dialog.asset.id, formData)
    }
    if (result.code !== 0) throw new Error(result.message)
    toast.success(t(dialog.type === 'register' ? 'admin.assets.registered' : 'admin.assets.saved'))
    resetDialog()
    await load()
  } catch (error) {
    toast.error(getApiErrorMessage(error, t(dialog.type === 'register' ? 'admin.assets.registerFailed' : 'admin.assets.saveFailed')))
  } finally {
    dialog.submitting = false
  }
}

onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>{{ t('navigation.resources') }}</span><h1>{{ t('navigation.referenceAssets') }}</h1><p>{{ t('admin.assets.description') }}</p></div><AppButton variant="primary" @click="openCreate"><Plus :size="15" />{{ t('admin.assets.upload') }}</AppButton></header>
    <form class="admin-filters admin-filters--assets" @submit.prevent="load"><AppSelect v-model="filters.resource_type" :options="resourceOptions" :aria-label="t('admin.assets.type')" /><AppSelect v-model="filters.active" :options="activeOptions" :aria-label="t('admin.assets.status')" /><AppButton type="submit" variant="primary"><Search :size="15" />{{ t('admin.assets.filter') }}</AppButton></form>
    <AppDataTable :columns="columns" :items="filteredItems" :loading="loading" :loading-title="t('admin.assets.loading')" :empty-title="t('admin.assets.empty')" min-width="980px">
      <template #cell-preview="{ item }"><div class="admin-asset-preview"><img :src="item.url" :alt="item.name" referrerpolicy="no-referrer" /><span><strong>{{ item.name }}</strong><small>{{ item.width || '—' }} × {{ item.height || '—' }}</small></span></div></template>
      <template #cell-resource_type="{ value }">{{ resourceLabel[value] || value }}</template>
      <template #cell-library="{ item }"><span class="admin-tags">{{ item.library?.tags?.length ? item.library.tags.join(' · ') : '—' }}</span></template>
      <template #cell-sort_order="{ value }">{{ n(value) }}</template>
      <template #cell-active="{ item }"><span class="admin-status" :class="item.active ? 'is-active' : 'is-disabled'">{{ t(item.active ? 'admin.assets.list' : 'admin.assets.unlist') }}</span></template>
      <template #cell-seedance="{ item }"><span v-if="item.resource_type === 'character'" class="admin-status" :class="`is-${item.seedance?.status || 'failed'}`">{{ item.seedance?.status || t('admin.assets.unregistered') }}</span><span v-else>—</span></template>
      <template #cell-actions="{ item }"><div class="admin-table-actions"><AppButton v-if="item.resource_type === 'character' && item.seedance?.status !== 'active'" size="sm" variant="soft" :title="t('admin.assets.retry')" @click="openRegister(item)"><RefreshCw :size="14" /></AppButton><AppButton size="sm" variant="soft" @click="openEdit(item)"><Pencil :size="14" />{{ t('common.edit') }}</AppButton></div></template>
    </AppDataTable>

    <AdminDialog v-if="dialog.type" v-model:reason="dialog.reason" :title="t(dialog.type === 'create' ? 'admin.assets.upload' : dialog.type === 'edit' ? 'admin.assets.edit' : 'admin.assets.retry')" :description="dialog.type === 'register' ? dialog.asset.name : t('admin.assets.hideNote')" :submitting="dialog.submitting" @close="resetDialog" @submit="submit">
      <template v-if="dialog.type === 'create'">
        <div class="admin-form-grid"><label class="admin-field"><span>{{ t('admin.assets.type') }}</span><AppSelect v-model="dialog.resourceType" :options="editableResourceOptions" :aria-label="t('admin.assets.type')" /></label><label class="admin-field"><span>{{ t('admin.assets.imageFile') }}</span><AppInput type="file" accept="image/jpeg,image/png,image/webp" required @change="fileChanged" /></label><label class="admin-field"><span>{{ t('admin.assets.name') }}</span><AppInput v-model="dialog.name" maxlength="100" required /></label><label class="admin-field"><span>{{ t('admin.assets.sortValue') }}</span><AppInput v-model="dialog.sortOrder" type="number" min="0" max="100000" required /></label><label class="admin-field admin-field--wide"><span>{{ t('admin.assets.tags') }}</span><AppInput v-model="dialog.tags" maxlength="400" :placeholder="t('admin.assets.tagPlaceholder')" /></label><label class="admin-field admin-field--wide"><span>{{ t('admin.assets.copyright') }}</span><AppInput v-model="dialog.copyrightNote" maxlength="500" :placeholder="t('admin.assets.adminOnly')" /></label></div>
      </template>
      <template v-else-if="dialog.type === 'edit'"><div class="admin-form-grid"><label class="admin-field"><span>{{ t('admin.assets.name') }}</span><AppInput v-model="dialog.name" maxlength="100" required /></label><label class="admin-field"><span>{{ t('admin.assets.sortValue') }}</span><AppInput v-model="dialog.sortOrder" type="number" min="0" max="100000" required /></label><label class="admin-field"><span>{{ t('admin.status') }}</span><AppSelect v-model="dialog.active" :options="enabledOptions" :aria-label="t('admin.assets.status')" /></label><label class="admin-field"><span>{{ t('admin.assets.tags') }}</span><AppInput v-model="dialog.tags" maxlength="400" :placeholder="t('admin.assets.tagPlaceholder')" /></label><label class="admin-field admin-field--wide"><span>{{ t('admin.assets.copyright') }}</span><AppInput v-model="dialog.copyrightNote" maxlength="500" :placeholder="t('admin.assets.adminOnly')" /></label></div></template>
      <p v-else class="admin-dialog-note">{{ t('admin.assets.retryNote') }}</p>
    </AdminDialog>
  </section>
</template>
