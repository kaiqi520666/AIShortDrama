<script setup>
import { LayoutGrid, ShoppingBag, X } from 'lucide-vue-next'
import { onBeforeUnmount } from 'vue'
import { workspaceTypes } from '../../config/canvas/nodePacks'
import AppButton from '../ui/AppButton.vue'

const props = defineProps({ submitting: Boolean })
const emit = defineEmits(['close', 'select'])
const icons = { general: LayoutGrid, ecommerce: ShoppingBag }

function close() {
  if (!props.submitting) emit('close')
}

function handleKeydown(event) {
  if (event.key === 'Escape') close()
}

window.addEventListener('keydown', handleKeydown)
onBeforeUnmount(() => window.removeEventListener('keydown', handleKeydown))
</script>

<template>
  <Teleport to="body">
    <div class="workspace-create-backdrop" @pointerdown.self="close">
      <section class="workspace-create-dialog" role="dialog" aria-modal="true" aria-labelledby="workspace-create-title">
        <header>
          <div><h2 id="workspace-create-title">{{ $t('workspace.new') }}</h2><p>{{ $t('workspace.selectType') }}</p></div>
          <AppButton icon-only :aria-label="$t('common.close')" :disabled="submitting" @click="close"><X :size="17" /></AppButton>
        </header>
        <div class="workspace-type-options">
          <AppButton
            v-for="option in workspaceTypes"
            :key="option.id"
            class="workspace-type-option"
            :disabled="submitting"
            @click="emit('select', option.id)"
          >
            <span><component :is="icons[option.id]" :size="20" /></span>
            <strong>{{ $t(`workspace.types.${option.id}.label`) }}</strong>
            <small>{{ $t(`workspace.types.${option.id}.description`) }}</small>
          </AppButton>
        </div>
      </section>
    </div>
  </Teleport>
</template>
