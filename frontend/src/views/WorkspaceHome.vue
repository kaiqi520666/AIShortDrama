<script setup>
import { computed, onMounted, ref } from 'vue'
import { Clapperboard, Copy, LogOut, Pencil, Play, Plus, Trash2 } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import AppButton from '../components/ui/AppButton.vue'
import AppInput from '../components/ui/AppInput.vue'
import AppSelect from '../components/ui/AppSelect.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { useGlobalConfirm, useGlobalToast } from '../composables/useGlobalUI'
import { useAuthStore } from '../stores/auth'
import { useWorkspaceStore } from '../stores/workspaces'

const router = useRouter()
const authStore = useAuthStore()
const store = useWorkspaceStore()
const toast = useGlobalToast()
const { confirm } = useGlobalConfirm()
const editingId = ref(null)
const sortBy = ref('updated')
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

async function run(action, successMessage) {
  try {
    const result = await action()
    if (successMessage) toast.success(successMessage)
    return result
  } catch (error) {
    toast.error(error.response?.data?.message || error.message || '操作失败')
  }
}

async function create() {
  await run(async () => router.push(`/workspaces/${(await store.create()).id}`))
}

async function signOut() {
  await authStore.logout()
  store.$reset()
  await router.replace('/')
}

async function rename(workspace, event) {
  const name = event.target.value.trim()
  editingId.value = null
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
  <main class="workspace-home">
    <header class="workspace-home-header">
      <div class="workspace-brand"><span class="brand-symbol"><Clapperboard :size="19" /></span><strong>Mooncut</strong><small>STUDIO</small></div>
      <div class="workspace-account">
        <span>{{ authStore.user?.username }}</span>
        <AppButton icon-only size="sm" title="退出登录" @click="signOut"><LogOut :size="16" /></AppButton>
      </div>
    </header>

    <section class="workspace-content">
      <div class="workspace-title-row">
        <div><span class="section-kicker">PROJECT LIBRARY</span><h1>创作项目</h1><p>从上次停下的位置继续推进镜头</p></div>
        <div class="workspace-filters"><span>{{ store.items.length }} 个项目</span><AppSelect v-model="sortBy" :options="sortOptions" aria-label="项目排序" /></div>
      </div>
      <p v-if="store.error" class="workspace-notice">{{ store.error }}</p>
      <EmptyState v-if="store.loading" class="workspace-empty" title="正在加载项目" loading />
      <div v-else class="workspace-grid">
        <AppButton class="workspace-create-card" aria-label="新建项目" @click="create">
          <span class="workspace-create-icon"><Plus :size="22" /></span>
          <strong>新建项目</strong>
          <small>创建新的工作流画布</small>
        </AppButton>
        <article v-for="(workspace, index) in displayedItems" :key="workspace.id" class="workspace-card" @dblclick="router.push(`/workspaces/${workspace.id}`)">
          <AppButton class="workspace-open-area" @click="router.push(`/workspaces/${workspace.id}`)">
            <span class="workspace-cover" aria-hidden="true"><b>{{ String(index + 1).padStart(2, '0') }}</b><i></i><Play :size="17" fill="currentColor" /></span>
            <span v-if="editingId !== workspace.id" class="workspace-card-name">{{ workspace.name }}</span>
            <small>WORKFLOW CANVAS</small>
          </AppButton>
          <AppInput
            v-if="editingId === workspace.id"
            class="workspace-name-input"
            :model-value="workspace.name"
            autofocus
            @click.stop
            @blur="rename(workspace, $event)"
            @keydown.enter="$event.target.blur()"
            @keydown.esc="editingId = null"
          />
          <footer>
            <time>{{ new Date(workspace.updated_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }}</time>
            <AppButton icon-only size="sm" title="重命名" @click="editingId = workspace.id"><Pencil :size="14" /></AppButton>
            <AppButton icon-only size="sm" title="复制" @click="duplicate(workspace)"><Copy :size="14" /></AppButton>
            <AppButton icon-only size="sm" title="删除" variant="danger" @click="remove(workspace)"><Trash2 :size="14" /></AppButton>
          </footer>
        </article>
      </div>
    </section>
  </main>
</template>
