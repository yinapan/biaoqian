<script setup lang="ts">
import { computed } from 'vue'
import { useSearchStore } from '@/stores/searchStore'

const store = useSearchStore()

const currentPage = computed({
  get: () => store.page,
  set: (p: number) => {
    store.setPage(p)
    store.doSearch()
  },
})

const totalPages = computed(() =>
  Math.ceil(store.total / store.pageSize),
)
</script>

<template>
  <div v-if="store.total > store.pageSize" class="pagination-bar">
    <div class="page-info">
      <span class="page-current" data-testid="page-current">{{ currentPage }}</span>
      <span class="page-sep">/</span>
      <span class="page-total">{{ totalPages }}</span>
    </div>

    <el-pagination
      v-model:current-page="currentPage"
      :page-size="store.pageSize"
      :total="store.total"
      layout="prev, pager, next"
      background
    />

    <div class="page-summary">
      共 <span class="summary-num">{{ store.total.toLocaleString() }}</span> 条
    </div>
  </div>
</template>

<style scoped>
.pagination-bar {
  margin-top: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 16px 0;
  border-top: 1px solid var(--border-subtle);
}

.page-info {
  font-family: var(--font-mono);
  font-size: 13px;
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.page-current {
  font-weight: 700;
  color: var(--accent-text);
  font-size: 16px;
}

.page-sep {
  color: var(--text-muted);
}

.page-total {
  color: var(--text-muted);
}

.page-summary {
  font-size: 12px;
  color: var(--text-muted);
}

.summary-num {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--text-secondary);
}
</style>
