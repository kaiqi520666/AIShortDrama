<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
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
const { confirmMutation } = useAdminMutation()
const loading = ref(false)
const items = ref([])
const filters = reactive({ resource_type: 'all', active: 'all' })
const dialog = reactive({ type: '', asset: null, file: null, name: '', sortOrder: '0', active: 'true', tags: '', copyrightNote: '', reason: '', submitting: false })
const resourceOptions = [{ value: 'all', label: '全部素材' }, { value: 'model', label: '系统模特' }, { value: 'character', label: '系统角色' }, { value: 'garment', label: '系统服饰' }]
const editableResourceOptions = resourceOptions.slice(1)
const activeOptions = [{ value: 'all', label: '全部状态' }, { value: 'active', label: '已上架' }, { value: 'inactive', label: '已下架' }]
const enabledOptions = [{ value: 'true', label: '上架' }, { value: 'false', label: '下架' }]
const columns = [
  { key: 'preview', label: '素材' },
  { key: 'resource_type', label: '类型' },
  { key: 'library', label: '标签' },
  { key: 'sort_order', label: '排序' },
  { key: 'active', label: '状态' },
  { key: 'seedance', label: '虚拟人像' },
  { key: 'actions', label: '操作', align: 'right' },
]
const resourceLabel = Object.fromEntries(resourceOptions.map((item) => [item.value, item.label]))
const filteredItems = computed(() => items.value)

async function load() {
  loading.value = true
  try {
    const result = await getAdminReferenceAssets({ ...filters })
    if (result.code !== 0) throw new Error(result.message)
    items.value = result.data
  } catch (error) {
    toast.error(getApiErrorMessage(error, '系统素材加载失败'))
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
  const action = dialog.type === 'create' ? '上传系统素材' : dialog.type === 'edit' ? '更新系统素材' : '重试虚拟人像注册'
  if (dialog.type === 'create' && !dialog.file) {
    toast.error('请选择图片文件')
    return
  }
  if (!await confirmMutation({
    title: action,
    message: dialog.type === 'register' ? `${dialog.asset.name} 将重新提交虚拟人像注册。` : `${dialog.name} 的系统素材配置将立即生效。`,
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
    toast.success(dialog.type === 'register' ? '虚拟人像注册已提交' : '系统素材已保存')
    resetDialog()
    await load()
  } catch (error) {
    toast.error(getApiErrorMessage(error, dialog.type === 'register' ? '虚拟人像注册失败' : '系统素材保存失败'))
  } finally {
    dialog.submitting = false
  }
}

onMounted(load)
</script>

<template>
  <section class="admin-page">
    <header class="admin-page__header"><div><span>REFERENCE LIBRARY</span><h1>系统素材库</h1><p>维护所有用户可选的系统模特、角色和服饰素材</p></div><AppButton variant="primary" @click="openCreate"><Plus :size="15" />上传素材</AppButton></header>
    <form class="admin-filters admin-filters--assets" @submit.prevent="load"><AppSelect v-model="filters.resource_type" :options="resourceOptions" aria-label="素材类型" /><AppSelect v-model="filters.active" :options="activeOptions" aria-label="素材状态" /><AppButton type="submit" variant="primary"><Search :size="15" />筛选</AppButton></form>
    <AppDataTable :columns="columns" :items="filteredItems" :loading="loading" loading-title="正在加载系统素材" empty-title="暂无系统素材" min-width="980px">
      <template #cell-preview="{ item }"><div class="admin-asset-preview"><img :src="item.url" :alt="item.name" referrerpolicy="no-referrer" /><span><strong>{{ item.name }}</strong><small>{{ item.width || '—' }} × {{ item.height || '—' }}</small></span></div></template>
      <template #cell-resource_type="{ value }">{{ resourceLabel[value] || value }}</template>
      <template #cell-library="{ item }"><span class="admin-tags">{{ item.library?.tags?.length ? item.library.tags.join(' · ') : '—' }}</span></template>
      <template #cell-active="{ item }"><span class="admin-status" :class="item.active ? 'is-active' : 'is-disabled'">{{ item.active ? '上架' : '下架' }}</span></template>
      <template #cell-seedance="{ item }"><span v-if="item.resource_type === 'character'" class="admin-status" :class="`is-${item.seedance?.status || 'failed'}`">{{ item.seedance?.status || '未注册' }}</span><span v-else>—</span></template>
      <template #cell-actions="{ item }"><div class="admin-table-actions"><AppButton v-if="item.resource_type === 'character' && item.seedance?.status !== 'active'" size="sm" variant="soft" title="重试虚拟人像注册" @click="openRegister(item)"><RefreshCw :size="14" /></AppButton><AppButton size="sm" variant="soft" @click="openEdit(item)"><Pencil :size="14" />编辑</AppButton></div></template>
    </AppDataTable>

    <AdminDialog v-if="dialog.type" v-model:reason="dialog.reason" :title="dialog.type === 'create' ? '上传系统素材' : dialog.type === 'edit' ? '编辑系统素材' : '重试虚拟人像注册'" :description="dialog.type === 'register' ? dialog.asset.name : '停用素材后将立即从用户选择器隐藏'" :submitting="dialog.submitting" @close="resetDialog" @submit="submit">
      <template v-if="dialog.type === 'create'">
        <div class="admin-form-grid"><label class="admin-field"><span>素材类型</span><AppSelect v-model="dialog.resourceType" :options="editableResourceOptions" aria-label="系统素材类型" /></label><label class="admin-field"><span>图片文件</span><AppInput type="file" accept="image/jpeg,image/png,image/webp" required @change="fileChanged" /></label><label class="admin-field"><span>素材名称</span><AppInput v-model="dialog.name" maxlength="100" required /></label><label class="admin-field"><span>排序值</span><AppInput v-model="dialog.sortOrder" type="number" min="0" max="100000" required /></label><label class="admin-field admin-field--wide"><span>标签</span><AppInput v-model="dialog.tags" maxlength="400" placeholder="多个标签用英文逗号分隔" /></label><label class="admin-field admin-field--wide"><span>版权备注</span><AppInput v-model="dialog.copyrightNote" maxlength="500" placeholder="仅后台可见" /></label></div>
      </template>
      <template v-else-if="dialog.type === 'edit'"><div class="admin-form-grid"><label class="admin-field"><span>素材名称</span><AppInput v-model="dialog.name" maxlength="100" required /></label><label class="admin-field"><span>排序值</span><AppInput v-model="dialog.sortOrder" type="number" min="0" max="100000" required /></label><label class="admin-field"><span>状态</span><AppSelect v-model="dialog.active" :options="enabledOptions" aria-label="素材状态" /></label><label class="admin-field"><span>标签</span><AppInput v-model="dialog.tags" maxlength="400" placeholder="多个标签用英文逗号分隔" /></label><label class="admin-field admin-field--wide"><span>版权备注</span><AppInput v-model="dialog.copyrightNote" maxlength="500" placeholder="仅后台可见" /></label></div></template>
      <p v-else class="admin-dialog-note">将使用当前素材图重新提交虚拟人像注册。失败状态会保留，方便再次重试。</p>
    </AdminDialog>
  </section>
</template>
