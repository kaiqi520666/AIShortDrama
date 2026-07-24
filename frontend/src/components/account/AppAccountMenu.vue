<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ChevronDown, LogOut, UserRound } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import { useGlobalConfirm } from '../../composables/useGlobalUI'
import AppButton from '../ui/AppButton.vue'
import AppMenu from '../ui/AppMenu.vue'

defineProps({ username: { type: String, required: true } })
const emit = defineEmits(['logout'])
const route = useRoute()
const router = useRouter()
const { confirm } = useGlobalConfirm()
const root = ref(null)
const trigger = ref(null)
const open = ref(false)
const activeIndex = ref(0)
const itemCount = 2

function openMenu() {
  activeIndex.value = 0
  open.value = true
}

function closeMenu(focus = false) {
  open.value = false
  if (focus) nextTick(() => trigger.value?.element?.focus())
}

async function openAccount() {
  closeMenu()
  if (route.name === 'account' && route.query.section === 'overview') return
  await router.push({ name: 'account', query: { section: 'overview' } })
}

async function logout() {
  closeMenu()
  const accepted = await confirm({
    title: '退出登录',
    message: '确定退出当前账号吗？',
    confirmText: '退出',
    tone: 'danger',
  })
  if (accepted) emit('logout')
}

function selectActive() {
  if (activeIndex.value === 0) openAccount()
  else logout()
}

function handleKeydown(event) {
  if (event.key === 'Escape' && open.value) {
    event.preventDefault()
    return closeMenu(true)
  }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    if (!open.value) return openMenu()
    activeIndex.value = (activeIndex.value + (event.key === 'ArrowDown' ? 1 : -1) + itemCount) % itemCount
  }
  if ((event.key === 'Enter' || event.key === ' ') && open.value) {
    event.preventDefault()
    selectActive()
  }
}

function handleOutside(event) {
  if (!root.value?.contains(event.target)) closeMenu()
}

onMounted(() => window.addEventListener('pointerdown', handleOutside))
onBeforeUnmount(() => window.removeEventListener('pointerdown', handleOutside))
</script>

<template>
  <div ref="root" class="account-menu" @keydown="handleKeydown">
    <AppButton
      ref="trigger"
      class="account-menu__trigger"
      type="button"
      size="sm"
      variant="soft"
      aria-haspopup="menu"
      :aria-expanded="open"
      @click="open ? closeMenu() : openMenu()"
    >
      <UserRound :size="15" />
      <span>{{ username }}</span>
      <ChevronDown class="account-menu__chevron" :size="14" />
    </AppButton>
    <Transition name="theme-menu">
      <AppMenu v-if="open" class="account-menu__popup" aria-label="账户菜单">
        <AppButton class="account-menu__item" role="menuitem" :class="{ active: activeIndex === 0 }" @pointerenter="activeIndex = 0" @click="openAccount">
          <UserRound :size="15" /><span>个人中心</span>
        </AppButton>
        <span class="account-menu__divider"></span>
        <AppButton class="account-menu__item account-menu__item--danger" role="menuitem" :class="{ active: activeIndex === 1 }" @pointerenter="activeIndex = 1" @click="logout">
          <LogOut :size="15" /><span>退出登录</span>
        </AppButton>
      </AppMenu>
    </Transition>
  </div>
</template>
