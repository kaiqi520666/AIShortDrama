<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId } from 'vue'
import { Check, ChevronDown } from 'lucide-vue-next'
import AppButton from './AppButton.vue'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, required: true },
  ariaLabel: { type: String, required: true },
})
const emit = defineEmits(['update:modelValue'])
const root = ref(null)
const trigger = ref(null)
const open = ref(false)
const activeIndex = ref(0)
const listboxId = useId()
const selectedOption = computed(() => props.options.find((option) => option.value === props.modelValue))

function selectedIndex() {
  const index = props.options.findIndex((option) => option.value === props.modelValue)
  return Math.max(0, index)
}

function openMenu() {
  activeIndex.value = selectedIndex()
  open.value = true
}

function closeMenu(focus = false) {
  open.value = false
  if (focus) nextTick(() => trigger.value?.element?.focus())
}

function selectOption(option) {
  if (option.disabled) return
  emit('update:modelValue', option.value)
  closeMenu(true)
}

function moveActive(step) {
  if (!props.options.length) return
  let index = activeIndex.value
  do index = (index + step + props.options.length) % props.options.length
  while (props.options[index].disabled && index !== activeIndex.value)
  activeIndex.value = index
}

function handleKeydown(event) {
  if (event.key === 'Tab') return closeMenu()
  if (event.key === 'Escape' && open.value) {
    event.preventDefault()
    return closeMenu(true)
  }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    if (!open.value) openMenu()
    else moveActive(event.key === 'ArrowDown' ? 1 : -1)
    return
  }
  if ((event.key === 'Enter' || event.key === ' ') && open.value) {
    event.preventDefault()
    selectOption(props.options[activeIndex.value])
  }
}

function handleOutside(event) {
  if (!root.value?.contains(event.target)) closeMenu()
}

onMounted(() => window.addEventListener('pointerdown', handleOutside, true))
onBeforeUnmount(() => window.removeEventListener('pointerdown', handleOutside, true))
</script>

<template>
  <div ref="root" v-bind="$attrs" class="ui-select" :class="{ open }" @keydown="handleKeydown">
    <AppButton
      ref="trigger"
      type="button"
      class="ui-select-trigger"
      :aria-label="ariaLabel"
      aria-haspopup="listbox"
      :aria-expanded="open"
      :aria-controls="listboxId"
      :aria-activedescendant="open ? `${listboxId}-${activeIndex}` : undefined"
      @click="open ? closeMenu() : openMenu()"
    >
      <span>{{ selectedOption?.label || $t('common.select') }}</span>
      <ChevronDown :size="14" aria-hidden="true" />
    </AppButton>
    <Transition name="ui-select-menu">
      <div v-if="open" :id="listboxId" class="ui-select-menu" role="listbox" :aria-label="ariaLabel">
        <AppButton
          v-for="(option, index) in options"
          :id="`${listboxId}-${index}`"
          :key="option.value"
          type="button"
          class="ui-select-option"
          role="option"
          tabindex="-1"
          :disabled="option.disabled"
          :aria-selected="option.value === modelValue"
          :class="{ active: index === activeIndex, selected: option.value === modelValue }"
          @pointerenter="activeIndex = index"
          @click="selectOption(option)"
        >
          <Check :size="14" :class="{ hidden: option.value !== modelValue }" />
          <span>{{ option.label }}</span>
        </AppButton>
      </div>
    </Transition>
  </div>
</template>
