<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { X } from 'lucide-vue-next'
import AppButton from '../ui/AppButton.vue'

defineEmits(['close'])

const closeButton = ref(null)
const sections = [
  { title: '创建', items: [['新建节点', ['Tab']], ['编组', ['Ctrl', 'G']], ['解组', ['Ctrl', 'Shift', 'G']], ['复制节点', ['Ctrl', 'D']]] },
  { title: '视图', items: [['放大', ['Ctrl', '+']], ['缩小', ['Ctrl', '-']], ['适应画布', ['Ctrl', '0']], ['整理画布', ['Alt', 'Shift', 'F']]] },
  { title: '工具', items: [['移动', ['V']], ['抓手工具', ['H']]] },
  { title: '其他', items: [['撤销', ['Ctrl', 'Z']], ['重做', ['Ctrl', 'Shift', 'Z']], ['删除', ['Delete']]] },
]

onMounted(() => nextTick(() => closeButton.value?.element?.focus()))
</script>

<template>
  <div class="shortcut-panel-backdrop" @pointerdown.self="$emit('close')">
    <section class="shortcut-panel" role="dialog" aria-modal="true" aria-labelledby="shortcut-panel-title">
      <header><h2 id="shortcut-panel-title">快捷键</h2><AppButton ref="closeButton" icon-only aria-label="关闭快捷键" @click="$emit('close')"><X :size="18" /></AppButton></header>
      <div class="shortcut-sections">
        <section v-for="section in sections" :key="section.title">
          <h3>{{ section.title }}</h3>
          <div v-for="item in section.items" :key="item[0]" class="shortcut-row">
            <span>{{ item[0] }}</span>
            <span><template v-for="(key, index) in item[1]" :key="key"><i v-if="index">+</i><kbd>{{ key }}</kbd></template></span>
          </div>
        </section>
      </div>
    </section>
  </div>
</template>
