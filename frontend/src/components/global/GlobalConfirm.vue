<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { CircleHelp, TriangleAlert } from 'lucide-vue-next'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import AppButton from '../ui/AppButton.vue'

const cancelButton = ref(null)
const { confirmState, acceptConfirm, cancelConfirm } = useGlobalConfirm()

function handleKeydown(event) {
  if (event.key === 'Escape' && confirmState.value) cancelConfirm()
}

watch(confirmState, (value) => {
  if (value) nextTick(() => cancelButton.value?.element?.focus())
})

window.addEventListener('keydown', handleKeydown)
onBeforeUnmount(() => window.removeEventListener('keydown', handleKeydown))
</script>

<template>
  <Teleport to="body">
    <Transition name="global-confirm">
      <div v-if="confirmState" class="global-confirm-backdrop" @pointerdown.self="cancelConfirm">
        <section class="global-confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="global-confirm-title" aria-describedby="global-confirm-message">
          <header>
            <span class="global-confirm-icon" :class="`global-confirm-icon--${confirmState.tone}`">
              <TriangleAlert v-if="confirmState.tone === 'danger'" :size="19" />
              <CircleHelp v-else :size="19" />
            </span>
            <div><h2 id="global-confirm-title">{{ confirmState.title }}</h2><p id="global-confirm-message">{{ confirmState.message }}</p></div>
          </header>
          <footer>
            <AppButton ref="cancelButton" variant="soft" @click="cancelConfirm">{{ confirmState.cancelText }}</AppButton>
            <AppButton :variant="confirmState.tone === 'danger' ? 'danger-solid' : 'primary'" @click="acceptConfirm">{{ confirmState.confirmText }}</AppButton>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>
