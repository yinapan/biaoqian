<script setup lang="ts">
import { computed } from 'vue'
import { useSearchStore } from '@/stores/searchStore'
import type { TagDefinition } from '@/types'

const props = defineProps<{
  definition: TagDefinition
}>()

const store = useSearchStore()

const field = computed(() => props.definition.field_name)

// Current filter value from store (reactive)
const selected = computed({
  get: () => store.filters[field.value] ?? (isMulti.value ? [] : null),
  set: (val: any) => {
    store.setFilter(field.value, val)
    store.doSearch()
  },
})

const isMulti = computed(() =>
  ['enum_single', 'enum_multi'].includes(props.definition.field_type),
)

const isRange = computed(() => props.definition.field_type === 'number_range')
const isBool = computed(() => props.definition.field_type === 'boolean')
const isText = computed(() => props.definition.field_type === 'text')

// For number_range: extract min/max from config
const rangeMin = computed(() => props.definition.config?.min ?? 0)
const rangeMax = computed(() => props.definition.config?.max ?? 100)
const rangeStep = computed(() => props.definition.config?.step ?? 1)

// Range value as [min, max] tuple
const rangeValue = computed({
  get: () => {
    const v = store.filters[field.value]
    if (Array.isArray(v) && v.length === 2) return v as [number, number]
    return [rangeMin.value, rangeMax.value] as [number, number]
  },
  set: (val: [number, number]) => {
    // Only set filter if range is narrowed from full extent
    if (val[0] === rangeMin.value && val[1] === rangeMax.value) {
      store.setFilter(field.value, null)
    } else {
      store.setFilter(field.value, val)
    }
    store.doSearch()
  },
})

// Boolean value
const boolValue = computed({
  get: () => {
    const v = store.filters[field.value]
    return v === true
  },
  set: (val: boolean) => {
    store.setFilter(field.value, val || null)
    store.doSearch()
  },
})
</script>

<template>
  <!-- text fields are not filterable in UI -->
  <div v-if="!isText" class="filter-group">
    <div class="group-label">{{ definition.display_name }}</div>

    <!-- Enum (checkbox group) -->
    <el-checkbox-group
      v-if="isMulti"
      v-model="selected"
      class="group-body"
    >
      <el-checkbox
        v-for="opt in definition.values"
        :key="opt.value"
        :label="opt.value"
        :value="opt.value"
      >
        {{ opt.display_name || opt.value }}
      </el-checkbox>
    </el-checkbox-group>

    <!-- Number range slider -->
    <el-slider
      v-else-if="isRange"
      v-model="rangeValue"
      range
      :min="rangeMin"
      :max="rangeMax"
      :step="rangeStep"
      class="group-body slider-body"
    />

    <!-- Boolean switch -->
    <el-switch v-else-if="isBool" v-model="boolValue" class="group-body" />
  </div>
</template>

<style scoped>
.filter-group {
  margin-bottom: 20px;
}

.group-label {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--el-text-color-primary);
}

.group-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.slider-body {
  padding: 0 8px;
}
</style>
