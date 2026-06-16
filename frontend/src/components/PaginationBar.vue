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
</script>

<template>
  <div v-if="store.total > store.pageSize" class="pagination-bar">
    <el-pagination
      v-model:current-page="currentPage"
      :page-size="store.pageSize"
      :total="store.total"
      layout="prev, pager, next, jumper, ->, total"
      background
    />
  </div>
</template>

<style scoped>
.pagination-bar {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
</style>
