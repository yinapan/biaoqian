<script setup lang="ts">
import { useSearchStore } from '@/stores/searchStore'

const store = useSearchStore()

const modules = [
  { type: 1, label: '模型', count: 'Model' },
  { type: 2, label: '特效', count: 'VFX' },
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
      <span class="module-label">{{ m.label }}</span>
      <span class="module-code">{{ m.count }}</span>
    </button>
  </nav>
</template>

<style scoped>
.module-nav {
  display: flex;
  gap: 2px;
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  padding: 4px;
  border: 1px solid var(--border-subtle);
}

.module-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  border: none;
  border-radius: 5px;
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.module-btn:hover {
  color: var(--text-primary);
  background: var(--bg-surface-hover);
}

.module-btn.active {
  background: var(--accent);
  color: var(--text-on-accent);
  box-shadow: 0 1px 2px rgba(18, 32, 47, 0.12);
}

.module-code {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  opacity: 0.65;
}

.module-label {
  font-size: 13px;
}
</style>
