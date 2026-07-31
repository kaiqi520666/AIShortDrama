<script setup>
import { nextTick, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  src: { type: String, required: true },
  previewSrc: { type: String, default: '' },
  alt: { type: String, default: '' },
  width: { type: Number, default: 360 },
})

const trigger = ref(null)
const preview = ref(null)
const visible = ref(false)
const position = ref({ left: '12px', top: '12px', width: '360px' })

function updatePosition() {
  if (!trigger.value) return
  const margin = 12
  const gap = 12
  const rect = trigger.value.getBoundingClientRect()
  const previewWidth = Math.min(props.width, window.innerWidth - margin * 2)
  const previewHeight = preview.value?.offsetHeight || Math.min(window.innerHeight * 0.7, previewWidth * 1.25)
  let left = rect.right + gap
  if (left + previewWidth > window.innerWidth - margin) left = rect.left - previewWidth - gap
  left = Math.max(margin, Math.min(left, window.innerWidth - previewWidth - margin))
  const top = Math.max(margin, Math.min(
    rect.top + (rect.height - previewHeight) / 2,
    window.innerHeight - previewHeight - margin,
  ))
  position.value = { left: `${left}px`, top: `${top}px`, width: `${previewWidth}px` }
}

async function showPreview() {
  if (!props.src) return
  visible.value = true
  updatePosition()
  window.addEventListener('resize', updatePosition)
  window.addEventListener('scroll', updatePosition, true)
  await nextTick()
  updatePosition()
}

function hidePreview() {
  visible.value = false
  window.removeEventListener('resize', updatePosition)
  window.removeEventListener('scroll', updatePosition, true)
}

onBeforeUnmount(hidePreview)
</script>

<template>
  <span ref="trigger" class="app-image-hover-preview-trigger" @mouseenter="showPreview" @mouseleave="hidePreview">
    <slot />
  </span>
  <Teleport to="body">
    <Transition name="app-image-hover-preview">
      <span v-if="visible" ref="preview" class="app-image-hover-preview" :style="position">
        <img :src="previewSrc || src" :alt="alt" referrerpolicy="no-referrer" @load="updatePosition" />
      </span>
    </Transition>
  </Teleport>
</template>

<style scoped>
.app-image-hover-preview-trigger {
  display: block;
  min-width: 0;
  min-height: 0;
}

.app-image-hover-preview {
  position: fixed;
  z-index: 400;
  display: grid;
  max-height: 70vh;
  place-items: center;
  overflow: hidden;
  pointer-events: none;
  border: 1px solid var(--color-border-strong);
  border-radius: 8px;
  background: var(--color-surface-base);
  box-shadow: var(--shadow-lg);
}

.app-image-hover-preview img {
  display: block;
  width: 100%;
  max-height: 70vh;
  object-fit: contain;
}

.app-image-hover-preview-enter-active,
.app-image-hover-preview-leave-active { transition: opacity 0.12s ease; }
.app-image-hover-preview-enter-from,
.app-image-hover-preview-leave-to { opacity: 0; }
</style>
