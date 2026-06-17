<script setup lang="ts">
import { onMounted } from 'vue'
import { useSearchStore } from '@/stores/searchStore'
import ModuleTabs from '@/components/ModuleTabs.vue'
import SearchBar from '@/components/SearchBar.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import ResultGrid from '@/components/ResultGrid.vue'
import PaginationBar from '@/components/PaginationBar.vue'

const store = useSearchStore()

onMounted(async () => {
  await store.loadDefinitions()
  await store.doSearch()
})
</script>

<template>
  <el-container class="search-page">
    <!-- Header -->
    <el-header class="search-header" height="auto">
      <h1 class="logo">美术标签搜索</h1>
      <ModuleTabs />
      <SearchBar />
    </el-header>

    <!-- Body -->
    <el-container class="search-body">
      <!-- Sidebar filters -->
      <el-aside class="filter-aside" width="280px">
        <FilterPanel />
      </el-aside>

      <!-- Main content -->
      <el-main class="result-main">
        <ResultGrid />
        <PaginationBar />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.search-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.search-header {
  padding: 16px 24px 12px;
  border-bottom: 1px solid var(--el-border-color-light);
  background: #fff;
}

.logo {
  margin: 0 0 12px;
  font-size: 20px;
  font-weight: 600;
  color: var(--el-color-primary);
}

.search-body {
  flex: 1;
  overflow: hidden;
}

.filter-aside {
  border-right: 1px solid var(--el-border-color-light);
  overflow-y: auto;
  background: #fafafa;
  padding: 16px;
}

.result-main {
  overflow-y: auto;
  padding: 16px 24px;
}
</style>
