<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { PencilLine } from 'lucide-vue-next'
import { useGlobalPrompt } from '../../composables/useGlobalUI'
import AppButton from '../ui/AppButton.vue'
import AppInput from '../ui/AppInput.vue'

const input = ref(null)
const value = ref('')
const { promptState, acceptPrompt, cancelPrompt } = useGlobalPrompt()

function submit() {
  const result = value.value.trim()
  if (result) acceptPrompt(result)
}

function handleKeydown(event) {
  if (event.key === 'Escape' && promptState.value) cancelPrompt()
}

watch(promptState, (state) => {
  if (!state) return
  value.value = state.value
  nextTick(() => input.value?.element?.select())
})

window.addEventListener('keydown', handleKeydown)
onBeforeUnmount(() => window.removeEventListener('keydown', handleKeydown))
</script>

<template>
  <Teleport to="body">
    <Transition name="global-confirm">
      <div v-if="promptState" class="global-confirm-backdrop" @pointerdown.self="cancelPrompt">
        <section class="global-confirm-dialog global-prompt-dialog" role="dialog" aria-modal="true" aria-labelledby="global-prompt-title" :aria-describedby="promptState.message ? 'global-prompt-message' : undefined">
          <header>
            <span class="global-confirm-icon"><PencilLine :size="18" /></span>
            <div><h2 id="global-prompt-title">{{ promptState.title }}</h2><p v-if="promptState.message" id="global-prompt-message">{{ promptState.message }}</p></div>
          </header>
          <form @submit.prevent="submit">
            <AppInput ref="input" v-model="value" :placeholder="promptState.placeholder" :maxlength="promptState.maxLength" :aria-label="promptState.title" />
            <footer>
              <AppButton type="button" variant="soft" @click="cancelPrompt">{{ promptState.cancelText }}</AppButton>
              <AppButton type="submit" variant="primary" :disabled="!value.trim()">{{ promptState.confirmText }}</AppButton>
            </footer>
          </form>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>
