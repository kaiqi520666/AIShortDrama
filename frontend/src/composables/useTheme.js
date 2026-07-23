import { computed, ref } from 'vue'

const STORAGE_KEY = 'mooncut-theme'
const validModes = new Set(['system', 'light', 'dark'])
const mode = ref('system')
const systemTheme = ref('light')
let mediaQuery

function applyTheme() {
  if (typeof document === 'undefined') return
  const theme = mode.value === 'system' ? systemTheme.value : mode.value
  document.documentElement.dataset.theme = theme
  document.documentElement.style.colorScheme = theme
}

function handleSystemTheme(event) {
  systemTheme.value = event.matches ? 'dark' : 'light'
  if (mode.value === 'system') applyTheme()
}

function readStoredMode() {
  if (typeof localStorage === 'undefined') return 'system'
  const stored = localStorage.getItem(STORAGE_KEY)
  return validModes.has(stored) ? stored : 'system'
}

export function initializeTheme() {
  mode.value = readStoredMode()
  if (typeof window !== 'undefined') {
    mediaQuery ??= window.matchMedia('(prefers-color-scheme: dark)')
    systemTheme.value = mediaQuery.matches ? 'dark' : 'light'
    mediaQuery.removeEventListener?.('change', handleSystemTheme)
    mediaQuery.addEventListener?.('change', handleSystemTheme)
  }
  applyTheme()
}

export function useTheme() {
  function setTheme(value) {
    mode.value = validModes.has(value) ? value : 'system'
    if (typeof localStorage !== 'undefined') localStorage.setItem(STORAGE_KEY, mode.value)
    applyTheme()
  }

  return {
    mode,
    resolvedTheme: computed(() => mode.value === 'system' ? systemTheme.value : mode.value),
    setTheme,
  }
}
