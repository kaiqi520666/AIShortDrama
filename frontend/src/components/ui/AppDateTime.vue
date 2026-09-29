<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { CalendarDays, ChevronLeft, ChevronRight, Clock3, X } from 'lucide-vue-next'
import AppButton from './AppButton.vue'
import AppSelect from './AppSelect.vue'
import { useI18n } from 'vue-i18n'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  modelValue: { type: String, default: '' },
  ariaLabel: { type: String, required: true },
  placeholder: { type: String, default: '' },
})
const { t, tm, locale } = useI18n()
const emit = defineEmits(['update:modelValue'])
const root = ref(null)
const open = ref(false)
const viewDate = ref(new Date())
const datePart = ref('')
const timePart = ref('00:00')

const monthLabel = computed(() => new Intl.DateTimeFormat(locale.value, { year: 'numeric', month: 'long' }).format(viewDate.value))
const hourOptions = computed(() => Array.from({ length: 24 }, (_, value) => ({ value: String(value).padStart(2, '0'), label: `${String(value).padStart(2, '0')} ${t('dateTime.hour')}` })))
const minuteOptions = computed(() => Array.from({ length: 60 }, (_, value) => ({ value: String(value).padStart(2, '0'), label: `${String(value).padStart(2, '0')} ${t('dateTime.minute')}` })))
const selectedHour = computed(() => timePart.value.slice(0, 2))
const selectedMinute = computed(() => timePart.value.slice(3, 5))
const calendarDays = computed(() => {
  const first = new Date(viewDate.value.getFullYear(), viewDate.value.getMonth(), 1)
  const start = new Date(first)
  start.setDate(first.getDate() - ((first.getDay() + 6) % 7))
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start)
    date.setDate(start.getDate() + index)
    const value = formatDate(date)
    return { date, value, day: date.getDate(), current: date.getMonth() === viewDate.value.getMonth(), selected: value === datePart.value }
  })
})
const displayValue = computed(() => props.modelValue ? props.modelValue.replace('T', ' ') : '')

function formatDate(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function syncValue() {
  if (!props.modelValue) {
    datePart.value = ''
    timePart.value = '00:00'
    return
  }
  const [date, time = '00:00'] = props.modelValue.split('T')
  datePart.value = date
  timePart.value = time.slice(0, 5)
  const parsed = new Date(`${date}T00:00:00`)
  if (!Number.isNaN(parsed.valueOf())) viewDate.value = parsed
}

function openPicker() {
  syncValue()
  open.value = true
  nextTick(() => root.value?.querySelector('.app-date-time__day.selected')?.focus())
}

function closePicker() { open.value = false }

function chooseDate(value) {
  datePart.value = value
  emitValue()
}

function updateTime(part, value) {
  const values = timePart.value.split(':')
  values[part === 'hour' ? 0 : 1] = value
  timePart.value = values.join(':')
  emitValue()
}

function emitValue() {
  if (datePart.value) emit('update:modelValue', `${datePart.value}T${timePart.value}`)
}

function shiftMonth(amount) {
  const next = new Date(viewDate.value)
  next.setMonth(next.getMonth() + amount)
  viewDate.value = next
}

function chooseToday() {
  const today = new Date()
  viewDate.value = today
  chooseDate(formatDate(today))
}

function clearValue() {
  emit('update:modelValue', '')
  closePicker()
}

function handleKeydown(event) {
  if (event.key === 'Escape' && open.value) {
    event.preventDefault()
    closePicker()
  }
}

function handleOutside(event) {
  if (!root.value?.contains(event.target)) closePicker()
}

onMounted(() => {
  syncValue()
  window.addEventListener('pointerdown', handleOutside)
  window.addEventListener('keydown', handleKeydown)
})
onBeforeUnmount(() => {
  window.removeEventListener('pointerdown', handleOutside)
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div ref="root" v-bind="$attrs" class="app-date-time" :class="{ open }">
    <AppButton type="button" class="app-date-time__trigger" :aria-label="ariaLabel" :aria-expanded="open" @click="open ? closePicker() : openPicker()">
      <CalendarDays :size="15" /><span>{{ displayValue || placeholder || t('dateTime.placeholder') }}</span><X v-if="displayValue" class="app-date-time__clear" :size="14" :aria-label="t('common.clear')" @click.stop="clearValue" /><ChevronRight v-else :size="14" />
    </AppButton>
    <div v-if="open" class="app-date-time__popover">
      <header><AppButton icon-only size="sm" :aria-label="t('dateTime.previousMonth')" @click="shiftMonth(-1)"><ChevronLeft :size="15" /></AppButton><strong>{{ monthLabel }}</strong><AppButton icon-only size="sm" :aria-label="t('dateTime.nextMonth')" @click="shiftMonth(1)"><ChevronRight :size="15" /></AppButton></header>
      <div class="app-date-time__weekdays"><span v-for="day in tm('dateTime.weekdays')" :key="day">{{ day }}</span></div>
      <div class="app-date-time__calendar"><AppButton v-for="item in calendarDays" :key="item.value" type="button" size="sm" class="app-date-time__day" :class="{ muted: !item.current, selected: item.selected }" @click="chooseDate(item.value)">{{ item.day }}</AppButton></div>
      <div class="app-date-time__time"><Clock3 :size="15" /><AppSelect :model-value="selectedHour" :options="hourOptions" :aria-label="t('dateTime.hour')" @update:model-value="updateTime('hour', $event)" /><span>:</span><AppSelect :model-value="selectedMinute" :options="minuteOptions" :aria-label="t('dateTime.minute')" @update:model-value="updateTime('minute', $event)" /></div>
      <footer><AppButton type="button" size="sm" variant="soft" @click="clearValue">{{ t('common.clear') }}</AppButton><AppButton type="button" size="sm" variant="soft" @click="chooseToday">{{ t('common.today') }}</AppButton></footer>
    </div>
  </div>
</template>
