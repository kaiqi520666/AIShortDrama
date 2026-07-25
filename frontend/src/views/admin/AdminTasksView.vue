<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Eye, Search } from 'lucide-vue-next'
import { getAdminTasks } from '../../api/admin'
import AdminDialog from '../../components/admin/AdminDialog.vue'
import AdminPagination from '../../components/admin/AdminPagination.vue'
import AppButton from '../../components/ui/AppButton.vue'
import AppDateTime from '../../components/ui/AppDateTime.vue'
import AppInput from '../../components/ui/AppInput.vue'
import AppSelect from '../../components/ui/AppSelect.vue'
import EmptyState from '../../components/ui/EmptyState.vue'
import { useGlobalToast } from '../../composables/useGlobalUI'

const toast = useGlobalToast()
const loading = ref(false)
const detail = ref(null)
const data = reactive({ items: [], page: 1, page_size: 20, total: 0 })
const filters = reactive({ q: '', media_type: 'all', model: '', status: '', start_at: '', end_at: '' })
const mediaOptions = [{ value: 'all', label: '全部类型' }, ...['text', 'image', 'video', 'audio'].map((value) => ({ value, label: ({ text: '文本', image: '图片', video: '视频', audio: '音频' })[value] }))]
async function load(page = 1) { loading.value = true; try { const params = { ...filters, page, page_size: data.page_size }; if (!params.start_at) delete params.start_at; if (!params.end_at) delete params.end_at; const result = await getAdminTasks(params); if (result.code !== 0) throw new Error(result.message); Object.assign(data, result.data) } catch (error) { toast.error(error.response?.data?.message || error.message || '任务加载失败') } finally { loading.value = false } }
function formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '—' }
function pretty(value) { return JSON.stringify(value ?? {}, null, 2) }
onMounted(load)
</script>

<template><section class="admin-page"><header class="admin-page__header"><div><span>GENERATION MONITOR</span><h1>生成任务</h1><p>查询全部生成任务与计费快照</p></div><b>{{ data.total }} 个任务</b></header><form class="admin-filters admin-filters--wide" @submit.prevent="load(1)"><label class="admin-search"><Search :size="15" /><AppInput v-model="filters.q" placeholder="用户名或邮箱" /></label><AppSelect v-model="filters.media_type" :options="mediaOptions" aria-label="任务类型" /><AppInput v-model="filters.model" placeholder="模型名称" /><AppInput v-model="filters.status" placeholder="任务状态" /><AppDateTime v-model="filters.start_at" aria-label="开始时间" placeholder="开始时间" /><AppDateTime v-model="filters.end_at" aria-label="结束时间" placeholder="结束时间" /><AppButton type="submit" variant="primary">查询</AppButton></form><EmptyState v-if="loading" title="正在加载生成任务" loading /><div v-else class="admin-table-wrap"><table class="admin-table"><thead><tr><th>用户</th><th>类型</th><th>模型</th><th>状态</th><th>积分</th><th>创建时间</th><th>详情</th></tr></thead><tbody><tr v-for="task in data.items" :key="task.id"><td><strong>{{ task.user.username }}</strong><small>{{ task.user.email }}</small></td><td>{{ task.task_type }}</td><td class="admin-model-cell">{{ task.model }}</td><td><span class="admin-status" :class="`is-${task.status}`">{{ task.status }}</span></td><td>{{ task.charged_credits }} / {{ task.frozen_credits }}</td><td>{{ formatDate(task.created_at) }}</td><td><AppButton size="sm" variant="soft" @click="detail = task"><Eye :size="14" />查看</AppButton></td></tr></tbody></table><EmptyState v-if="!data.items.length" title="没有符合条件的任务" /></div><AdminPagination :page="data.page" :page-size="data.page_size" :total="data.total" @change="load" /><AdminDialog v-if="detail" title="任务详情" :description="detail.id" :reason-required="false" confirm-text="关闭" @close="detail = null" @submit="detail = null"><dl class="admin-detail-list"><div><dt>状态</dt><dd>{{ detail.status }} · {{ detail.progress }}%</dd></div><div><dt>错误</dt><dd>{{ detail.error_message || '—' }}</dd></div></dl><h3 class="admin-detail-title">请求快照</h3><pre class="admin-json">{{ pretty(detail.request_snapshot) }}</pre><h3 class="admin-detail-title">计费快照</h3><pre class="admin-json">{{ pretty(detail.pricing_snapshot) }}</pre><h3 class="admin-detail-title">结果快照</h3><pre class="admin-json">{{ pretty(detail.result) }}</pre></AdminDialog></section></template>
