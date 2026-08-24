<script>
let scriptPromise

function loadScript() {
  if (window.turnstile) return Promise.resolve(window.turnstile)
  scriptPromise ||= new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit'
    script.async = true
    script.defer = true
    script.dataset.turnstileScript = 'true'
    script.addEventListener('load', () => resolve(window.turnstile), { once: true })
    script.addEventListener('error', reject, { once: true })
    document.head.appendChild(script)
  }).catch((error) => {
    scriptPromise = undefined
    throw error
  })
  return scriptPromise
}
</script>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  siteKey: { type: String, required: true },
  action: { type: String, required: true },
  resetKey: { type: Number, default: 0 },
})
const emit = defineEmits(['verified', 'expired', 'error'])
const container = ref(null)
const failed = ref(false)
let widgetId = null

async function render() {
  if (!props.siteKey || widgetId !== null) return
  try {
    const turnstile = await loadScript()
    await nextTick()
    if (!container.value) return
    widgetId = turnstile.render(container.value, {
      sitekey: props.siteKey,
      action: props.action,
      theme: 'auto',
      size: 'flexible',
      callback: (token) => emit('verified', token),
      'expired-callback': () => emit('expired'),
      'error-callback': () => emit('error'),
    })
  } catch {
    failed.value = true
    emit('error')
  }
}

watch(() => props.siteKey, render)
watch(() => props.resetKey, () => {
  if (widgetId !== null) window.turnstile?.reset(widgetId)
})
onMounted(render)
onBeforeUnmount(() => {
  if (widgetId !== null) window.turnstile?.remove(widgetId)
})
</script>

<template>
  <div class="auth-turnstile">
    <div ref="container" class="auth-turnstile-widget"></div>
    <p v-if="!siteKey">正在加载人机验证...</p>
    <p v-else-if="failed">人机验证加载失败，请刷新重试</p>
  </div>
</template>
