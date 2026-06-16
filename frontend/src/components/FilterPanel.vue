<script setup lang="ts">
import { useSearchStore } from '@/stores/searchStore'
import FilterGroup from './FilterGroup.vue'

const store = useSearchStore()
</script>

<template>
  <div class="filter-panel">
    <h3 class="panel-title">筛选条件</h3>
    <template v-if="store.tagDefinitions.length">
      <FilterGroup
        v-for="def in store.tagDefinitions.filter((d) => d.is_filterable)"
        :key="def.field_name"
        :definition="def"
      />
    </template>
    <el-empty v-else description="暂无筛选维度" :image-size="60" />
  </div>
</template>

<style scoped>
.panel-title {
  margin: 0 0 16px;
  font-size: 15px;
  font-weight: 600;
}
</style>
