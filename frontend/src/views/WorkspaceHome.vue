<script setup>
import { onMounted, ref } from 'vue'
import { Clapperboard, Copy, FolderOpen, Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { useWorkspaceStore } from '../stores/workspaces'

const emit = defineEmits(['open'])
const store = useWorkspaceStore()
const editingId = ref(null)
const notice = ref('')

async function run(action) {
  notice.value = ''
  try {
    await action()
  } catch (error) {
    notice.value = error.response?.data?.message || error.message || '操作失败'
  }
}

async function create() {
  await run(async () => emit('open', (await store.create()).id))
}

async function rename(workspace, event) {
  const name = event.target.value.trim()
  editingId.value = null
  if (name && name !== workspace.name) await run(() => store.rename(workspace.id, name))
}

onMounted(() => store.load())
</script>

<template>
  <main class="workspace-home">
    <header class="workspace-home-header">
      <div class="workspace-brand"><Clapperboard :size="20" /><strong>Mooncut</strong></div>
      <button class="workspace-create" @click="create"><Plus :size="17" />新建工作台</button>
    </header>

    <section class="workspace-content">
      <div class="workspace-title-row">
        <div><h1>工作台</h1><p>打开一张画布继续创作</p></div>
        <span>{{ store.items.length }} 个</span>
      </div>
      <p v-if="notice || store.error" class="workspace-notice">{{ notice || store.error }}</p>
      <div v-if="store.loading" class="workspace-empty">加载中…</div>
      <div v-else-if="!store.items.length" class="workspace-empty">暂无工作台</div>
      <div v-else class="workspace-grid">
        <article v-for="workspace in store.items" :key="workspace.id" class="workspace-card" @dblclick="emit('open', workspace.id)">
          <button class="workspace-open-area" @click="emit('open', workspace.id)">
            <FolderOpen :size="28" />
            <span v-if="editingId !== workspace.id">{{ workspace.name }}</span>
          </button>
          <input
            v-if="editingId === workspace.id"
            class="workspace-name-input"
            :value="workspace.name"
            autofocus
            @click.stop
            @blur="rename(workspace, $event)"
            @keydown.enter="$event.target.blur()"
            @keydown.esc="editingId = null"
          />
          <footer>
            <time>{{ new Date(workspace.updated_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }}</time>
            <button title="重命名" @click="editingId = workspace.id"><Pencil :size="14" /></button>
            <button title="复制" @click="run(() => store.duplicate(workspace.id))"><Copy :size="14" /></button>
            <button title="删除" @click="run(() => store.remove(workspace.id))"><Trash2 :size="14" /></button>
          </footer>
        </article>
      </div>
    </section>
  </main>
</template>
