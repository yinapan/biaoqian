<script setup lang="ts">
import { useSearchStore } from '@/stores/searchStore'

const store = useSearchStore()

const modules = [
  { type: 1, label: '模型' },
  { type: 2, label: '特效' },
]

function selectModule(mod: number) {
  store.setModuleType(mod)
  store.loadDefinitions().then(() => store.doSearch())
}
</script>

<template>
  <nav class="module-nav">
    <button
      v-for="m in modules"
      :key="m.type"
      class="module-btn"
      :class="{ active: store.moduleType === m.type }"
      @click="selectModule(m.type)"
    >
      {{ m.label }}
    </button>
  </nav>
</template>

<style scoped>
.module-nav {
  display: flex;
  gap: 4px;
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  padding: 3px;
  border: 1px solid var(--border-subtle);
}

.module-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--text-muted);
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.module-btn:hover {
  color: var(--text-secondary);
  background: var(--bg-surface-hover);
}

.module-btn.active {
  background: var(--accent);
  color: var(--text-on-accent);
}
</style>
