<script setup>
import { computed, onMounted, ref } from 'vue'
import { Copy, Pencil, Play, Plus, Trash2 } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import WorkspaceCreateDialog from '../../components/workspace/WorkspaceCreateDialog.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useGlobalConfirm, useGlobalPrompt, useGlobalToast } from '../../composables/useGlobalUI'
import { getWorkspaceType } from '../../config/canvas/nodePacks'
import { useWorkspaceStore } from '../../stores/workspaces'

const router = useRouter()
const store = useWorkspaceStore()
const toast = useGlobalToast()
const { confirm } = useGlobalConfirm()
const { prompt } = useGlobalPrompt()
const sortBy = ref('created')
const createDialogOpen = ref(false)
const creating = ref(false)
const sortOptions = [
  { value: 'updated', label: '最近更新' },
  { value: 'created', label: '最近创建' },
  { value: 'name', label: '名称排序' },
]
const displayedItems = computed(() => store.items.toSorted((a, b) => {
  if (sortBy.value === 'name') return a.name.localeCompare(b.name, 'zh-CN')
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
    toast.error(error.response?.data?.message || error.message || '操作失败')
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
    title: '重命名项目',
    message: '输入新的项目名称',
    value: workspace.name,
    placeholder: '项目名称',
    maxLength: 100,
  })
  if (name && name !== workspace.name) await run(() => store.rename(workspace.id, name), '项目名称已更新')
}

async function duplicate(workspace) {
  await run(() => store.duplicate(workspace.id), '项目副本已创建')
}

async function remove(workspace) {
  const accepted = await confirm({
    title: '删除项目',
    message: `确定删除“${workspace.name}”吗？此操作无法撤销。`,
    confirmText: '删除',
    tone: 'danger',
  })
  if (accepted) await run(() => store.remove(workspace.id), '项目已删除')
}

onMounted(() => store.load())
</script>

<template>
  <section class="workspace-content">
    <div class="workspace-title-row">
      <div><span class="section-kicker">PROJECT LIBRARY</span><h1>创作项目</h1><p>从上次停下的位置继续推进镜头</p></div>
      <div class="workspace-filters"><span>{{ store.items.length }} 个项目</span><AppSelect v-model="sortBy" :options="sortOptions" aria-label="项目排序" /></div>
    </div>
    <p v-if="store.error" class="workspace-notice">{{ store.error }}</p>
    <EmptyState v-if="store.loading" class="workspace-empty" title="正在加载项目" loading />
    <div v-else class="workspace-grid">
      <AppButton class="workspace-create-card" aria-label="新建项目" @click="createDialogOpen = true">
        <span class="workspace-create-icon"><Plus :size="22" /></span>
        <strong>新建项目</strong>
        <small>创建新的工作流画布</small>
      </AppButton>
      <article v-for="workspace in displayedItems" :key="workspace.id" class="workspace-card" @dblclick="router.push({ name: 'canvas', params: { workspaceId: workspace.id } })">
        <AppButton class="workspace-open-area" @click="router.push({ name: 'canvas', params: { workspaceId: workspace.id } })">
          <span class="workspace-cover" :class="{ 'has-image': workspace.thumbnail_url }" aria-hidden="true">
            <img v-if="workspace.thumbnail_url" :src="workspace.thumbnail_url" alt="" loading="lazy" referrerpolicy="no-referrer" />
            <b>{{ workspaceNumbers.get(workspace.id) }}</b><i></i><Play :size="17" fill="currentColor" />
          </span>
          <span class="workspace-card-name">{{ workspace.name }}</span>
          <small>{{ getWorkspaceType(workspace.workspace_type).label }}</small>
        </AppButton>
        <footer>
          <time>{{ new Date(workspace.created_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }}</time>
          <AppButton icon-only size="sm" title="重命名" @click="rename(workspace)"><Pencil :size="14" /></AppButton>
          <AppButton icon-only size="sm" title="复制" @click="duplicate(workspace)"><Copy :size="14" /></AppButton>
          <AppButton icon-only size="sm" title="删除" variant="danger" @click="remove(workspace)"><Trash2 :size="14" /></AppButton>
        </footer>
      </article>
    </div>
    <WorkspaceCreateDialog v-if="createDialogOpen" :submitting="creating" @close="createDialogOpen = false" @select="create" />
  </section>
</template>
