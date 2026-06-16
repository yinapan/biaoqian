<script setup lang="ts">
import { useSearchStore } from '@/stores/searchStore'
import AssetCard from './AssetCard.vue'

const store = useSearchStore()
</script>

<template>
  <div class="result-grid">
    <!-- Summary -->
    <div class="result-summary">
      <span v-if="!store.loading && store.response">
        共 <strong>{{ store.total }}</strong> 条结果
        <span class="query-time">({{ store.response.query_time_ms }}ms)</span>
      </span>
    </div>

    <!-- Loading skeleton -->
    <template v-if="store.loading">
      <el-row :gutter="16">
        <el-col v-for="i in 8" :key="i" :xs="24" :sm="12" :md="8" :lg="6">
          <el-skeleton :rows="4" animated style="margin-bottom: 16px" />
        </el-col>
      </el-row>
    </template>

    <!-- Results -->
    <template v-else-if="store.items.length">
      <el-row :gutter="16">
        <el-col
          v-for="item in store.items"
          :key="item.id"
          :xs="24"
          :sm="12"
          :md="8"
          :lg="6"
        >
          <AssetCard :item="item" />
        </el-col>
      </el-row>
    </template>

    <!-- Empty state -->
    <el-empty v-else description="暂无搜索结果" />
  </div>
</template>

<style scoped>
.result-summary {
  margin-bottom: 16px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.query-time {
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}
</style>
