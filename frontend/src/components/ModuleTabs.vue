<script setup lang="ts">
import { useSearchStore } from '@/stores/searchStore'

const store = useSearchStore()

const modules = [
  { type: 1, label: '模型', icon: '◆' },
  { type: 2, label: '特效', icon: '✦' },
  { type: 3, label: '动作', icon: '▸' },
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
      <span class="module-icon">{{ m.icon }}</span>
      <span class="module-label">{{ m.label }}</span>
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
  box-shadow: 0 1px 4px rgba(232, 168, 56, 0.3);
}

.module-icon {
  font-size: 10px;
  line-height: 1;
}

.module-btn.active .module-icon {
  opacity: 0.7;
}
</style>
