<script setup>
import AppButton from '../ui/AppButton.vue'

defineProps({ page: { type: Number, required: true }, pageSize: { type: Number, required: true }, total: { type: Number, required: true } })
const emit = defineEmits(['change'])
</script>

<template>
  <footer class="admin-pagination"><span>共 {{ total }} 条</span><div><AppButton size="sm" variant="soft" :disabled="page <= 1" @click="emit('change', page - 1)">上一页</AppButton><b>{{ page }} / {{ Math.max(1, Math.ceil(total / pageSize)) }}</b><AppButton size="sm" variant="soft" :disabled="page * pageSize >= total" @click="emit('change', page + 1)">下一页</AppButton></div></footer>
</template>
