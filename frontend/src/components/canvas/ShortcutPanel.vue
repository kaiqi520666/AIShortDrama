<script setup>
import { useI18n } from 'vue-i18n'
import { computed, nextTick, onMounted, ref } from 'vue'
import { X } from 'lucide-vue-next'
import AppButton from '../ui/AppButton.vue'

const { t } = useI18n()

defineEmits(['close'])

const closeButton = ref(null)
const sections = computed(() => ([
  { title: t('canvas.create'), items: [[t('canvas.createNode'), ['Tab']], [t('canvas.groupMerge'), ['Ctrl', 'G']], [t('canvas.ungroupShort'), ['Ctrl', 'Shift', 'G']], [t('canvas.connect'), ['Ctrl', 'L']], [t('canvas.duplicateNodesEdges'), ['Ctrl', 'D']], [t('canvas.generate'), ['Ctrl', 'Enter']]] },
  { title: t('canvas.view'), items: [[t('canvas.zoomIn'), ['Ctrl', '+']], [t('canvas.zoomOut'), ['Ctrl', '-']], [t('canvas.fitCanvas'), ['Ctrl', '0']], [t('canvas.arrangeCanvas'), ['Alt', 'Shift', 'F']]] },
  { title: t('canvas.tools'), items: [[t('canvas.move'), ['V']], [t('canvas.handTool'), ['H']], [t('canvas.temporaryHand'), ['Space']], [t('canvas.dragDuplicate'), ['Alt', t('canvas.drag')]]] },
  { title: t('canvas.other'), items: [[t('canvas.undo'), ['Ctrl', 'Z']], [t('canvas.redo'), ['Ctrl', 'Shift', 'Z']], [t('canvas.delete'), ['Delete']]] },
]))

onMounted(() => nextTick(() => closeButton.value?.element?.focus()))
</script>

<template>
  <div class="shortcut-panel-backdrop" @pointerdown.self="$emit('close')">
    <section class="shortcut-panel" role="dialog" aria-modal="true" :aria-label="t('canvas.shortcuts')">
      <header><AppButton ref="closeButton" icon-only :aria-label="t('canvas.closeShortcuts')" @click="$emit('close')"><X :size="18" /></AppButton></header>
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
