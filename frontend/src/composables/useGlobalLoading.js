import { computed, readonly, ref } from 'vue'

const tasks = ref([])
const visible = computed(() => tasks.value.length > 0)
const message = computed(() => tasks.value.at(-1)?.message || '加载中…')

function showLoading(taskMessage = '加载中…') {
  const id = crypto.randomUUID()
  tasks.value = [...tasks.value, { id, message: taskMessage }]
  return id
}

function hideLoading(id) {
  tasks.value = id ? tasks.value.filter((task) => task.id !== id) : tasks.value.slice(0, -1)
}

export function useGlobalLoading() {
  return {
    visible: readonly(visible),
    message: readonly(message),
    showLoading,
    hideLoading,
    clearLoading: () => { tasks.value = [] },
  }
}
