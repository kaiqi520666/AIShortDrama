<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { Check, Monitor, Moon, Sun } from 'lucide-vue-next'
import { useTheme } from '../../composables/useTheme'
import AppButton from './AppButton.vue'
import AppMenu from './AppMenu.vue'

const options = [
  { value: 'system', label: '跟随系统', icon: Monitor },
  { value: 'light', label: '明亮模式', icon: Sun },
  { value: 'dark', label: '暗黑模式', icon: Moon },
]
const root = ref(null)
const trigger = ref(null)
const open = ref(false)
const activeIndex = ref(0)
const { mode, resolvedTheme, setTheme } = useTheme()
const currentIcon = computed(() => mode.value === 'system' ? Monitor : resolvedTheme.value === 'dark' ? Moon : Sun)

function openMenu() {
  activeIndex.value = Math.max(0, options.findIndex((option) => option.value === mode.value))
  open.value = true
}

function closeMenu(focus = false) {
  open.value = false
  if (focus) nextTick(() => trigger.value?.element?.focus())
}

function selectMode(value) {
  setTheme(value)
  closeMenu(true)
}

function handleKeydown(event) {
  if (event.key === 'Escape' && open.value) {
    event.preventDefault()
    return closeMenu(true)
  }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    if (!open.value) return openMenu()
    activeIndex.value = (activeIndex.value + (event.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length
  }
  if ((event.key === 'Enter' || event.key === ' ') && open.value) {
    event.preventDefault()
    selectMode(options[activeIndex.value].value)
  }
}

function handleOutside(event) {
  if (!root.value?.contains(event.target)) closeMenu()
}

onMounted(() => window.addEventListener('pointerdown', handleOutside))
onBeforeUnmount(() => window.removeEventListener('pointerdown', handleOutside))
</script>

<template>
  <div ref="root" class="theme-switch" @keydown="handleKeydown">
    <AppButton
      ref="trigger"
      type="button"
      class="theme-switch__trigger"
      icon-only
      size="sm"
      :title="`主题：${options.find((option) => option.value === mode)?.label}`"
      aria-label="切换显示主题"
      aria-haspopup="menu"
      :aria-expanded="open"
      @click="open ? closeMenu() : openMenu()"
    >
      <component :is="currentIcon" :size="16" />
    </AppButton>
    <Transition name="theme-menu">
      <AppMenu v-if="open" class="theme-switch__menu" aria-label="显示主题">
        <AppButton
          v-for="(option, index) in options"
          :key="option.value"
          class="theme-switch__option"
          type="button"
          role="menuitemradio"
          :aria-checked="mode === option.value"
          :class="{ active: index === activeIndex }"
          @pointerenter="activeIndex = index"
          @click="selectMode(option.value)"
        >
          <component :is="option.icon" :size="15" />
          <span>{{ option.label }}</span>
          <Check :size="14" :class="{ hidden: mode !== option.value }" />
        </AppButton>
      </AppMenu>
    </Transition>
  </div>
</template>
