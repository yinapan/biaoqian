<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useSearchStore } from '@/stores/searchStore'
import ModuleTabs from '@/components/ModuleTabs.vue'
import SearchBar from '@/components/SearchBar.vue'
import FilterPanel from '@/components/FilterPanel.vue'
import ResultGrid from '@/components/ResultGrid.vue'
import PaginationBar from '@/components/PaginationBar.vue'

const store = useSearchStore()

const moduleName = computed(() => (store.moduleType === 2 ? '特效资源' : '模型资源'))

onMounted(async () => {
  await store.loadDefinitions()
  await store.doSearch()
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand-block">
        <img src="/logo.png" alt="Logo" class="brand-logo" />
        <div class="brand-text">
          <h1>美术标签搜索平台</h1>
          <span>模型与特效资产检索工作台</span>
        </div>
      </div>

      <div class="topbar-center">
        <ModuleTabs />
      </div>

      <div class="topbar-right">
        <SearchBar />
      </div>
    </header>

    <div class="main-area">
      <aside class="sidebar">
        <FilterPanel />
      </aside>

      <main class="content">
        <div class="workspace-head">
          <div>
            <div class="eyebrow">当前模块</div>
            <h2>{{ moduleName }}</h2>
          </div>
          <div class="workspace-metrics">
            <span class="metric">
              <strong>{{ store.total.toLocaleString() }}</strong>
              <span>结果</span>
            </span>
            <span class="metric">
              <strong>{{ Object.keys(store.filters).length }}</strong>
              <span>筛选</span>
            </span>
            <span v-if="store.response" class="metric">
              <strong>{{ store.response.query_time_ms }}</strong>
              <span>ms</span>
            </span>
          </div>
        </div>
        <section class="results-panel">
          <ResultGrid />
          <PaginationBar />
        </section>
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
  gap: 24px;
  padding: 0 28px;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
  z-index: 10;
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 260px;
}

.topbar-center {
  flex-shrink: 0;
}

.topbar-right {
  flex: 1;
  max-width: 640px;
  min-width: 280px;
}

.brand-logo {
  width: 34px;
  height: 34px;
  object-fit: contain;
}

.brand-text {
  min-width: 0;
}

.brand-text h1 {
  font-size: 16px;
  line-height: 20px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0;
}

.brand-text span {
  display: block;
  margin-top: 2px;
  font-size: 12px;
  line-height: 16px;
  color: var(--text-muted);
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
  background: #f8fafc;
  border-right: 1px solid var(--border-subtle);
  overflow: hidden;
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
}

/* --- Content --- */
.content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 28px 28px;
}

.workspace-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 16px;
}

.eyebrow {
  font-size: 12px;
  line-height: 16px;
  color: var(--text-muted);
}

.workspace-head h2 {
  margin-top: 2px;
  font-size: 22px;
  line-height: 30px;
  color: var(--text-primary);
  font-weight: 700;
}

.workspace-metrics {
  display: flex;
  align-items: center;
  gap: 8px;
}

.metric {
  display: inline-flex;
  align-items: baseline;
  gap: 5px;
  padding: 7px 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
}

.metric strong {
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--text-primary);
}

.metric span {
  font-size: 12px;
  color: var(--text-muted);
}

.results-panel {
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 18px;
  box-shadow: var(--shadow-card);
}

@media (max-width: 980px) {
  .topbar {
    height: auto;
    flex-wrap: wrap;
    padding: 14px 16px;
  }

  .brand-block {
    min-width: 0;
  }

  .topbar-right {
    order: 3;
    max-width: none;
    width: 100%;
    flex-basis: 100%;
  }

  .main-area {
    flex-direction: column;
  }

  .sidebar {
    width: 100%;
    max-height: 340px;
    border-right: none;
    border-bottom: 1px solid var(--border-subtle);
  }

  .content {
    padding: 16px;
  }

  .workspace-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
