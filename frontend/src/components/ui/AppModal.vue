<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { X } from 'lucide-vue-next'
import AppButton from './AppButton.vue'

defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
})
const emit = defineEmits(['close'])
const closeButton = ref(null)

function handleKeydown(event) {
  if (event.key === 'Escape') emit('close')
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
  nextTick(() => closeButton.value?.element?.focus())
})
onBeforeUnmount(() => window.removeEventListener('keydown', handleKeydown))
</script>

<template>
  <Teleport to="body">
    <Transition name="app-modal">
      <div class="app-modal-backdrop" @pointerdown.self="emit('close')">
        <section class="app-modal" role="dialog" aria-modal="true" aria-labelledby="app-modal-title">
          <header class="app-modal-header">
            <div><h2 id="app-modal-title">{{ title }}</h2><p v-if="description">{{ description }}</p></div>
            <div class="app-modal-header-actions">
              <slot name="header-actions" />
              <AppButton ref="closeButton" icon-only size="sm" title="关闭" aria-label="关闭" @click="emit('close')"><X :size="17" /></AppButton>
            </div>
          </header>
          <div class="app-modal-body"><slot /></div>
          <footer v-if="$slots.footer" class="app-modal-footer"><slot name="footer" /></footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>
