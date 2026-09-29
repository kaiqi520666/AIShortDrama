<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { formatDateTime } from '../../i18n'
import { Copy, Pencil, Play, Plus, Trash2 } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import WorkspaceCreateDialog from '../../components/workspace/WorkspaceCreateDialog.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useGlobalConfirm, useGlobalPrompt, useGlobalToast } from '../../composables/useGlobalUI'
import { getWorkspaceType } from '../../config/canvas/nodePacks'
import { useWorkspaceStore } from '../../stores/workspaces'
import { getApiErrorMessage } from '../../utils/apiError'
import { buildOssImageUrl } from '../../utils/ossImage'

const router = useRouter()
const { t, locale, n } = useI18n()
const store = useWorkspaceStore()
const toast = useGlobalToast()
const { confirm } = useGlobalConfirm()
const { prompt } = useGlobalPrompt()
const sortBy = ref('created')
const createDialogOpen = ref(false)
const creating = ref(false)
const sortOptions = computed(() => [
  { value: 'updated', label: t('workspace.updated') },
  { value: 'created', label: t('workspace.created') },
  { value: 'name', label: t('workspace.nameSort') },
])
const displayedItems = computed(() => store.items.toSorted((a, b) => {
  if (sortBy.value === 'name') return a.name.localeCompare(b.name, locale.value)
  const key = sortBy.value === 'created' ? 'created_at' : 'updated_at'
  return new Date(b[key]) - new Date(a[key])
}))
const workspaceNumbers = computed(() => new Map(
  store.items
    .toSorted((a, b) => new Date(a.created_at) - new Date(b.created_at))
    .map((workspace, index) => [workspace.id, String(index + 1).padStart(2, '0')]),
))

async function run(action, successMessage) {
  try {
    const result = await action()
    if (successMessage) toast.success(successMessage)
    return result
  } catch (error) {
    toast.error(getApiErrorMessage(error, t('common.operationFailed')))
  }
}

async function create(workspaceType) {
  creating.value = true
  try {
    const workspace = await run(() => store.create(workspaceType))
    if (!workspace) return
    createDialogOpen.value = false
    await router.push({ name: 'canvas', params: { workspaceId: workspace.id } })
  } finally {
    creating.value = false
  }
}

async function rename(workspace) {
  const name = await prompt({
    title: t('workspace.rename'),
    message: t('workspace.renameDescription'),
    value: workspace.name,
    placeholder: t('workspace.name'),
    maxLength: 100,
  })
  if (name && name !== workspace.name) await run(() => store.rename(workspace.id, name), t('workspace.renamed'))
}

async function duplicate(workspace) {
  await run(() => store.duplicate(workspace.id), t('workspace.duplicated'))
}

async function remove(workspace) {
  const accepted = await confirm({
    title: t('workspace.delete'),
    message: t('workspace.deleteConfirmation', { name: workspace.name }),
    confirmText: t('common.delete'),
    tone: 'danger',
  })
  if (accepted) await run(() => store.remove(workspace.id), t('workspace.deleted'))
}

onMounted(() => store.load())
</script>

<template>
  <section class="workspace-content">
    <div class="workspace-title-row">
      <div><span class="section-kicker">{{ t('workspace.library') }}</span><h1>{{ t('workspace.title') }}</h1><p>{{ t('workspace.description') }}</p></div>
      <div class="workspace-filters"><span>{{ t('workspace.count', { count: n(store.items.length) }) }}</span><AppSelect v-model="sortBy" :options="sortOptions" :aria-label="t('workspace.sort')" /></div>
    </div>
    <p v-if="store.error" class="workspace-notice">{{ store.error }}</p>
    <EmptyState v-if="store.loading" class="workspace-empty" :title="t('workspace.loading')" loading />
    <div v-else class="workspace-grid">
      <AppButton class="workspace-create-card" :aria-label="t('workspace.new')" @click="createDialogOpen = true">
        <span class="workspace-create-icon"><Plus :size="22" /></span>
        <strong>{{ t('workspace.new') }}</strong>
        <small>{{ t('workspace.newDescription') }}</small>
      </AppButton>
      <article v-for="workspace in displayedItems" :key="workspace.id" class="workspace-card" @dblclick="router.push({ name: 'canvas', params: { workspaceId: workspace.id } })">
        <AppButton class="workspace-open-area" @click="router.push({ name: 'canvas', params: { workspaceId: workspace.id } })">
          <span class="workspace-cover" :class="{ 'has-image': workspace.thumbnail_url }" aria-hidden="true">
            <img v-if="workspace.thumbnail_url" :src="buildOssImageUrl(workspace.thumbnail_url, { width: 480, quality: 80 })" alt="" loading="lazy" referrerpolicy="no-referrer" />
            <b>{{ workspaceNumbers.get(workspace.id) }}</b><i></i><Play :size="17" fill="currentColor" />
          </span>
          <span class="workspace-card-name">{{ workspace.name }}</span>
          <small>{{ t(`workspace.types.${getWorkspaceType(workspace.workspace_type).id}.label`) }}</small>
        </AppButton>
        <footer>
          <time>{{ formatDateTime(workspace.created_at, { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }}</time>
          <AppButton icon-only size="sm" :title="t('common.rename')" @click="rename(workspace)"><Pencil :size="14" /></AppButton>
          <AppButton icon-only size="sm" :title="t('common.copy')" @click="duplicate(workspace)"><Copy :size="14" /></AppButton>
          <AppButton icon-only size="sm" :title="t('common.delete')" variant="danger" @click="remove(workspace)"><Trash2 :size="14" /></AppButton>
        </footer>
      </article>
    </div>
    <WorkspaceCreateDialog v-if="createDialogOpen" :submitting="creating" @close="createDialogOpen = false" @select="create" />
  </section>
</template>
