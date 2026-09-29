<script setup>
import { computed } from 'vue'
import AppButton from './AppButton.vue'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  columns: { type: Array, required: true },
  items: { type: Array, default: () => [] },
  rowKey: { type: [String, Function], default: 'id' },
  loading: { type: Boolean, default: false },
  loadingTitle: { type: String, default: '' },
  emptyTitle: { type: String, default: '' },
  emptyDescription: { type: String, default: '' },
  minWidth: { type: String, default: '720px' },
  pagination: { type: Object, default: null },
})

const emit = defineEmits(['page-change'])
const totalPages = computed(() => Math.max(1, Math.ceil((props.pagination?.total || 0) / (props.pagination?.pageSize || 1))))

function itemKey(item, index) {
  return typeof props.rowKey === 'function' ? props.rowKey(item) : item[props.rowKey] ?? index
}
</script>

<template>
  <div class="app-data-table">
    <EmptyState v-if="loading" compact loading :title="loadingTitle || $t('common.loading')" />
    <EmptyState v-else-if="!items.length" compact :title="emptyTitle || $t('common.empty')" :description="emptyDescription" />
    <template v-else>
      <div class="app-data-table__scroll">
        <table class="app-data-table__table" :style="{ minWidth }">
          <thead>
            <tr>
              <th
                v-for="column in columns"
                :key="column.key"
                :class="column.align ? `app-data-table__cell--${column.align}` : undefined"
                :style="column.width ? { width: column.width } : undefined"
              >{{ column.label }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(item, index) in items" :key="itemKey(item, index)">
              <td
                v-for="column in columns"
                :key="column.key"
                :class="[column.class, column.align ? `app-data-table__cell--${column.align}` : undefined]"
              >
                <slot :name="`cell-${column.key}`" :item="item" :value="item[column.key]">
                  {{ item[column.key] ?? '—' }}
                </slot>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <footer v-if="pagination" class="app-data-table__pagination">
        <span>{{ $t('common.totalRecords', { count: $n(pagination.total) }) }}</span>
        <div>
          <AppButton variant="soft" :disabled="pagination.page <= 1" @click="emit('page-change', pagination.page - 1)">{{ $t('common.previousPage') }}</AppButton>
          <b>{{ $n(pagination.page) }} / {{ $n(totalPages) }}</b>
          <AppButton variant="soft" :disabled="pagination.page >= totalPages" @click="emit('page-change', pagination.page + 1)">{{ $t('common.nextPage') }}</AppButton>
        </div>
      </footer>
    </template>
  </div>
</template>
