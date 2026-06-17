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
  <div class="app-shell">
    <!-- Top bar -->
    <header class="topbar">
      <div class="topbar-left">
        <div class="brand">
          <img src="/logo.png" alt="Logo" class="brand-logo" />
        </div>
        <ModuleTabs />
      </div>
      <div class="topbar-right">
        <SearchBar />
      </div>
    </header>

    <!-- Main content area -->
    <div class="main-area">
      <!-- Sidebar -->
      <aside class="sidebar">
        <FilterPanel />
      </aside>

      <!-- Content -->
      <main class="content">
        <ResultGrid />
        <PaginationBar />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-root);
  overflow: hidden;
}

/* --- Top Bar --- */
.topbar {
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
  z-index: 10;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 32px;
}

.topbar-right {
  flex: 1;
  max-width: 560px;
  margin-left: 40px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.brand-logo {
  height: 32px;
  width: auto;
  object-fit: contain;
}

/* --- Main Area --- */
.main-area {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* --- Sidebar --- */
.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  background: var(--bg-elevated);
  border-right: 1px solid var(--border-subtle);
  overflow: hidden;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
}

/* --- Content --- */
.content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px;
}
</style>
