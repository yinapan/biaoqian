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
          <span class="brand-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" fill="var(--accent)" opacity="0.8"/>
              <path d="M2 17l10 5 10-5" stroke="var(--accent)" stroke-width="1.5" fill="none" opacity="0.5"/>
              <path d="M2 12l10 5 10-5" stroke="var(--accent)" stroke-width="1.5" fill="none" opacity="0.7"/>
            </svg>
          </span>
          <h1 class="brand-text">美术资源</h1>
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

.brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: var(--accent-soft);
  border-radius: var(--radius-sm);
  border: 1px solid rgba(232, 168, 56, 0.15);
}

.brand-text {
  font-size: 17px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--text-primary);
  white-space: nowrap;
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
