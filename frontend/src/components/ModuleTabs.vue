<script setup lang="ts">
import { computed } from 'vue'
import { useSearchStore } from '@/stores/searchStore'

const store = useSearchStore()

const MODULE_MAP: Record<string, number> = {
  model: 1,
  effect: 2,
  animation: 3,
}

const activeTab = computed({
  get: () => {
    const entry = Object.entries(MODULE_MAP).find(
      ([, v]) => v === store.moduleType,
    )
    return entry ? entry[0] : 'model'
  },
  set: (tab: string) => {
    const mod = MODULE_MAP[tab] ?? 1
    store.setModuleType(mod)
    store.loadDefinitions().then(() => store.doSearch())
  },
})
</script>

<template>
  <el-tabs v-model="activeTab" class="module-tabs">
    <el-tab-pane label="模型" name="model" />
    <el-tab-pane label="特效" name="effect" />
    <el-tab-pane label="动作" name="animation" />
  </el-tabs>
</template>

<style scoped>
.module-tabs {
  margin-bottom: 12px;
}
</style>
