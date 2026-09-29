<script setup>
import { useI18n } from 'vue-i18n'
import { nextTick, onMounted, ref, watch } from 'vue'
import { Image, Music2, Video as VideoIcon } from 'lucide-vue-next'
import { buildOssImageUrl } from '../../utils/ossImage'
import AppButton from '../ui/AppButton.vue'
import AppImageHoverPreview from '../ui/AppImageHoverPreview.vue'
import AppMenu from '../ui/AppMenu.vue'

const { t, locale } = useI18n()

const props = defineProps({
  modelValue: { type: Array, required: true },
  references: { type: Array, required: true },
  referenceType: { type: String, default: 'image' },
  referenceLabel: { type: String, default: '' },
  placeholder: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])
const editor = ref(null)
const menu = ref(null)
const menuVisible = ref(false)
const menuStyle = ref({})
const activeIndex = ref(0)
let mentionRange = null
const referenceLabels = { image: 'canvas.image', video: 'canvas.video', audio: 'canvas.audio' }

function getReferenceType(reference) {
  return reference?.type || props.referenceType
}

function getReferenceLabel(type) {
  return referenceLabels[type] ? t(referenceLabels[type]) : props.referenceLabel || t('canvas.image')
}

function getReferenceNumber(reference) {
  const type = getReferenceType(reference)
  return props.references.filter((item) => getReferenceType(item) === type).findIndex((item) => item.id === reference.id) + 1
}

function createToken(part) {
  const reference = props.references.find((item) => item.id === part.nodeId)
  const type = getReferenceType(reference || part)
  const token = document.createElement('span')
  const label = document.createElement('span')
  token.className = 'prompt-reference-token'
  token.contentEditable = 'false'
  token.dataset.nodeId = part.nodeId
  token.dataset.mentionId = part.id
  token.dataset.referenceType = type
  token.title = reference.data.title
  if (type === 'image') {
    const image = document.createElement('img')
    image.src = buildOssImageUrl(reference.data.asset)
    image.alt = ''
    token.append(image)
  }
  label.className = 'prompt-reference-label'
  label.textContent = getReferenceLabel(type)
  token.append(label)
  return token
}

function renumberTokens() {
  editor.value.querySelectorAll('.prompt-reference-token').forEach((token) => {
    const reference = props.references.find((item) => item.id === token.dataset.nodeId)
    if (reference) token.querySelector('.prompt-reference-label').textContent = `${getReferenceLabel(getReferenceType(reference))}${getReferenceNumber(reference)}`
  })
}

function renderEditor() {
  const fragment = document.createDocumentFragment()
  props.modelValue.forEach((part) => {
    if (part.nodeId && props.references.some((item) => item.id === part.nodeId)) fragment.append(createToken(part))
    else if (part.value) fragment.append(document.createTextNode(part.value))
  })
  editor.value.replaceChildren(fragment)
  renumberTokens()
}

function appendText(parts, value) {
  if (!value) return
  const last = parts.at(-1)
  if (last?.type === 'text') last.value += value
  else parts.push({ type: 'text', value })
}

function readNode(node, parts) {
  if (node.nodeType === 3) return appendText(parts, node.textContent)
  if (node.nodeType !== 1) return
  if (node.classList.contains('prompt-reference-token')) {
    parts.push({ type: node.dataset.referenceType, id: node.dataset.mentionId, nodeId: node.dataset.nodeId })
    return
  }
  if (node.tagName === 'BR') return appendText(parts, '\n')
  node.childNodes.forEach((child) => readNode(child, parts))
  if ((node.tagName === 'DIV' || node.tagName === 'P') && node.nextSibling) appendText(parts, '\n')
}

function syncParts() {
  const parts = []
  editor.value.childNodes.forEach((node) => readNode(node, parts))
  renumberTokens()
  emit('update:modelValue', parts)
}

function updateMenuPosition() {
  if (!mentionRange || !editor.value) return
  const menuElement = menu.value?.element || menu.value?.$el || menu.value
  const rangeRect = mentionRange.getBoundingClientRect()
  const editorRect = editor.value.getBoundingClientRect()
  const anchor = rangeRect.width || rangeRect.height ? rangeRect : editorRect
  const width = menuElement?.offsetWidth || Math.min(360, window.innerWidth - 24)
  const height = menuElement?.offsetHeight || 180
  const left = Math.min(Math.max(12, anchor.left), window.innerWidth - width - 12)
  const below = anchor.bottom + 8
  const top = below + height <= window.innerHeight - 12 ? below : Math.max(12, anchor.top - height - 8)
  menuStyle.value = { left: `${left}px`, top: `${top}px` }
}

function hasMentionTrigger() {
  const container = mentionRange?.startContainer
  const offset = mentionRange?.startOffset
  return container?.nodeType === 3 && container.textContent[offset - 1] === '@'
}

function handleInput(event) {
  syncParts()
  if (event.data !== '@') {
    if (menuVisible.value && !hasMentionTrigger()) menuVisible.value = false
    return
  }
  const selection = window.getSelection()
  if (!selection.rangeCount) return
  mentionRange = selection.getRangeAt(0).cloneRange()
  activeIndex.value = 0
  menuVisible.value = true
  nextTick(updateMenuPosition)
}

function handlePaste(event) {
  event.preventDefault()
  const clipboard = event.clipboardData
  if (!clipboard || Array.from(clipboard.items).some((item) => item.kind === 'file')) return
  const text = clipboard.getData('text/plain').replace(/\r\n?/g, '\n')
  if (!text) return
  const selection = window.getSelection()
  if (!selection.rangeCount) return
  const range = selection.getRangeAt(0)
  if (!editor.value.contains(range.commonAncestorContainer)) return
  range.deleteContents()
  const node = document.createTextNode(text)
  range.insertNode(node)
  range.setStartAfter(node)
  range.collapse(true)
  selection.removeAllRanges()
  selection.addRange(range)
  syncParts()
}

function insertReference(reference) {
  if (!mentionRange) return
  const container = mentionRange.startContainer
  const offset = mentionRange.startOffset
  if (container.nodeType === 3 && container.textContent[offset - 1] === '@') mentionRange.setStart(container, offset - 1)
  mentionRange.deleteContents()
  const token = createToken({ type: getReferenceType(reference), id: crypto.randomUUID(), nodeId: reference.id })
  const space = document.createTextNode(' ')
  mentionRange.insertNode(token)
  token.after(space)
  mentionRange.setStartAfter(space)
  mentionRange.collapse(true)
  const selection = window.getSelection()
  selection.removeAllRanges()
  selection.addRange(mentionRange)
  menuVisible.value = false
  editor.value.focus()
  syncParts()
}

function handleKeydown(event) {
  if (!menuVisible.value) return
  if (event.key === 'Escape') {
    menuVisible.value = false
    return
  }
  if (!props.references.length) return
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    const step = event.key === 'ArrowDown' ? 1 : -1
    activeIndex.value = (activeIndex.value + step + props.references.length) % props.references.length
  }
  if (event.key === 'Enter') {
    event.preventDefault()
    insertReference(props.references[activeIndex.value])
  }
}

watch([() => props.modelValue, () => props.references], () => {
  if (document.activeElement !== editor.value) renderEditor()
}, { deep: true })
watch(menuVisible, (visible) => {
  if (visible) nextTick(updateMenuPosition)
})
watch(locale, renumberTokens)
onMounted(renderEditor)
</script>

<template>
  <div class="prompt-reference-editor">
    <div
      ref="editor"
      class="prompt-editor-content"
      contenteditable="plaintext-only"
      role="textbox"
      :aria-label="t('canvas.referencePrompt', { p0: referenceLabel || t('canvas.image') })"
      aria-multiline="true"
      :data-placeholder="placeholder"
      @input="handleInput"
      @paste="handlePaste"
      @keydown="handleKeydown"
      @scroll="updateMenuPosition"
      @blur="menuVisible = false"
    ></div>

    <AppMenu v-if="menuVisible" ref="menu" class="prompt-reference-menu" :style="menuStyle" @pointerdown.prevent>
      <AppButton
        v-for="(reference, index) in references"
        :key="reference.id"
        :class="{ active: activeIndex === index }"
        @mouseenter="activeIndex = index"
        @click="insertReference(reference)"
      >
        <AppImageHoverPreview v-if="getReferenceType(reference) === 'image'" :src="reference.data.asset" :preview-src="buildOssImageUrl(reference.data.asset, { width: 1200, quality: 90 })" :alt="reference.data.title">
          <img :src="buildOssImageUrl(reference.data.asset)" alt="" />
        </AppImageHoverPreview>
        <VideoIcon v-else-if="getReferenceType(reference) === 'video'" :size="24" />
        <Music2 v-else-if="getReferenceType(reference) === 'audio'" :size="24" />
        <Image v-else :size="24" />
        <span>{{ reference.data.title }}</span>
      </AppButton>
      <p v-if="!references.length">{{ t('canvas.noReferences') }}</p>
    </AppMenu>
  </div>
</template>
