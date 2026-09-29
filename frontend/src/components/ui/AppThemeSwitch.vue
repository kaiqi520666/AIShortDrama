<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { Check, Monitor, Moon, Sun } from 'lucide-vue-next'
import { useTheme } from '../../composables/useTheme'
import { useI18n } from 'vue-i18n'
import AppButton from './AppButton.vue'
import AppMenu from './AppMenu.vue'

const options = [
  { value: 'system', key: 'system', icon: Monitor },
  { value: 'light', key: 'light', icon: Sun },
  { value: 'dark', key: 'dark', icon: Moon },
]
const { t } = useI18n()
const root = ref(null)
const trigger = ref(null)
const open = ref(false)
const activeIndex = ref(0)
const { mode, resolvedTheme, activateTheme, deactivateTheme, setTheme } = useTheme()
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

onMounted(() => {
  activateTheme()
  window.addEventListener('pointerdown', handleOutside)
})
onBeforeUnmount(() => {
  deactivateTheme()
  window.removeEventListener('pointerdown', handleOutside)
})
</script>

<template>
  <div ref="root" class="theme-switch" @keydown="handleKeydown">
    <AppButton
      ref="trigger"
      type="button"
      class="theme-switch__trigger"
      icon-only
      size="sm"
      :title="t('theme.title', { mode: t(`theme.${options.find((option) => option.value === mode)?.key}`) })"
      :aria-label="t('theme.aria')"
      aria-haspopup="menu"
      :aria-expanded="open"
      @click="open ? closeMenu() : openMenu()"
    >
      <component :is="currentIcon" :size="16" />
    </AppButton>
    <Transition name="theme-menu">
      <AppMenu v-if="open" class="theme-switch__menu" :aria-label="t('theme.menu')">
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
          <span>{{ t(`theme.${option.key}`) }}</span>
          <Check :size="14" :class="{ hidden: mode !== option.value }" />
        </AppButton>
      </AppMenu>
    </Transition>
  </div>
</template>
