<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Array, required: true },
  references: { type: Array, required: true },
  placeholder: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])
const editor = ref(null)
const menu = ref(null)
const menuVisible = ref(false)
const menuStyle = ref({})
const activeIndex = ref(0)
let mentionRange = null

function createToken(part) {
  const reference = props.references.find((item) => item.id === part.nodeId)
  const token = document.createElement('span')
  const image = document.createElement('img')
  const label = document.createElement('span')
  token.className = 'prompt-image-token'
  token.contentEditable = 'false'
  token.dataset.nodeId = part.nodeId
  token.dataset.mentionId = part.id
  token.title = reference.data.title
  image.src = reference.data.asset
  image.alt = ''
  label.className = 'prompt-image-label'
  label.textContent = '图片'
  token.append(image, label)
  return token
}

function renumberTokens() {
  editor.value.querySelectorAll('.prompt-image-token').forEach((token) => {
    const imageNumber = props.references.findIndex((item) => item.id === token.dataset.nodeId) + 1
    token.querySelector('.prompt-image-label').textContent = `图片${imageNumber}`
  })
}

function renderEditor() {
  const fragment = document.createDocumentFragment()
  props.modelValue.forEach((part) => {
    if (part.type === 'image') {
      if (props.references.some((item) => item.id === part.nodeId)) fragment.append(createToken(part))
    } else {
      fragment.append(document.createTextNode(part.value))
    }
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
  if (node.classList.contains('prompt-image-token')) {
    parts.push({ type: 'image', id: node.dataset.mentionId, nodeId: node.dataset.nodeId })
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
  const rangeRect = mentionRange.getBoundingClientRect()
  const editorRect = editor.value.getBoundingClientRect()
  const anchor = rangeRect.width || rangeRect.height ? rangeRect : editorRect
  const width = menu.value?.offsetWidth || Math.min(360, window.innerWidth - 24)
  const height = menu.value?.offsetHeight || 180
  const left = Math.min(Math.max(12, anchor.left), window.innerWidth - width - 12)
  const below = anchor.bottom + 8
  const top = below + height <= window.innerHeight - 12 ? below : Math.max(12, anchor.top - height - 8)
  menuStyle.value = { left: `${left}px`, top: `${top}px` }
}

function handleInput(event) {
  syncParts()
  if (event.data !== '@') return
  const selection = window.getSelection()
  if (!selection.rangeCount) return
  mentionRange = selection.getRangeAt(0).cloneRange()
  activeIndex.value = 0
  menuVisible.value = true
  nextTick(updateMenuPosition)
}

function insertReference(reference) {
  if (!mentionRange) return
  const container = mentionRange.startContainer
  const offset = mentionRange.startOffset
  if (container.nodeType === 3 && container.textContent[offset - 1] === '@') mentionRange.setStart(container, offset - 1)
  mentionRange.deleteContents()
  const token = createToken({ id: crypto.randomUUID(), nodeId: reference.id })
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

watch(() => props.modelValue, () => {
  if (document.activeElement !== editor.value) renderEditor()
}, { deep: true })
watch(menuVisible, (visible) => {
  if (visible) nextTick(updateMenuPosition)
})
onMounted(renderEditor)
</script>

<template>
  <div class="prompt-reference-editor">
    <div
      ref="editor"
      class="prompt-editor-content"
      contenteditable="true"
      role="textbox"
      aria-label="图片提示词"
      aria-multiline="true"
      :data-placeholder="placeholder"
      @input="handleInput"
      @keydown="handleKeydown"
      @blur="menuVisible = false"
    ></div>

    <div v-if="menuVisible" ref="menu" class="prompt-reference-menu" :style="menuStyle" @pointerdown.prevent>
      <button
        v-for="(reference, index) in references"
        :key="reference.id"
        :class="{ active: activeIndex === index }"
        @mouseenter="activeIndex = index"
        @click="insertReference(reference)"
      >
        <img :src="reference.data.asset" alt="" />
        <span>{{ reference.data.title }}</span>
      </button>
      <p v-if="!references.length">暂无可引用资产，请连入后操作</p>
    </div>
  </div>
</template>
