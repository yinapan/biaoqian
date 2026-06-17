<script setup lang="ts">
import { computed, ref } from 'vue'
import { useSearchStore } from '@/stores/searchStore'
import type { AssetItem } from '@/types'

const props = defineProps<{
  item: AssetItem
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
}>()

const store = useSearchStore()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const copied = ref(false)

function copyPath() {
  const text = props.item.resource_path
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).catch(() => fallbackCopy(text))
  } else {
    fallbackCopy(text)
  }
  copied.value = true
  setTimeout(() => (copied.value = false), 1500)
}

function fallbackCopy(text: string) {
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.position = 'fixed'
  ta.style.opacity = '0'
  document.body.appendChild(ta)
  ta.select()
  document.execCommand('copy')
  document.body.removeChild(ta)
}

const isEffect = computed(() => store.moduleType === 2)

const previewSrc = computed(() => {
  if (!props.item.thumbnail_path) return ''
  if (isEffect.value) {
    return `/data/gifs/${props.item.thumbnail_path}`
  }
  return `/static/previews/${props.item.thumbnail_path}`
})

const effectGridSrc = computed(() => {
  if (!isEffect.value || !props.item.thumbnail_path) return ''
  const gridName = props.item.thumbnail_path.replace('.gif', '_grid.gif')
  return `/data/gifs/${gridName}`
})

const tagEntries = computed(() => Object.entries(props.item.tags))

const TAG_LABELS: Record<string, string> = {
  species: '物种',
  gender: '性别',
  region: '地域',
  faction: '势力',
  profession: '职业',
  body_type: '体型',
  age_group: '年龄',
  clothing: '衣着',
  features: '特征',
  exclusive_npc: '专属NPC',
  remark: '备注',
  action_module: '动作模组',
  action_type: '动作类型',
  slot_name: '插槽',
  source_sheet: '来源表',
  color: '颜色',
  form_structure: '形态结构',
  time_dynamic: '时间动态',
  element: '元素属性',
  combat_skill: '战斗技能',
  scene_env: '场景环境',
  scope_size: '范围大小',
  status_buff: '状态Buff',
  magic_circle: '法阵地面',
  ui_hint: 'UI提示',
  biz_usage: '业务用途',
  char_action: '角色动作',
  item_prop: '道具物品',
  description: '描述',
  effect_duration_sec: '特效时长',
}

/** Group definitions for detail view: fields in the same group are merged into one row */
const TAG_GROUPS: Record<string, { label: string; fields: string[]; unit?: string }> = {
  dimensions: { label: '尺寸 (cm)', fields: ['length_cm', 'width_cm', 'height_cm'], unit: 'cm' },
  camera: { label: '相机参数', fields: ['camera_distance', 'camera_scale'] },
  coverage: { label: '画面占比', fields: ['area_ratio', 'span_max'] },
}

const GROUPED_FIELDS = new Set(Object.values(TAG_GROUPS).flatMap(g => g.fields))

const FIELD_SHORT_LABELS: Record<string, string> = {
  length_cm: '长', width_cm: '宽', height_cm: '高',
  camera_distance: '距离', camera_scale: '缩放',
  area_ratio: '面积', span_max: '跨度',
}

/** Tag entries excluding grouped fields and hidden internal fields */
const visibleTagEntries = computed(() =>
  tagEntries.value.filter(([key]) => !GROUPED_FIELDS.has(key))
)

/** Grouped numeric entries that exist in this item's tags */
const activeGroups = computed(() => {
  const result: Array<{ label: string; items: Array<{ short: string; value: any }> }> = []
  for (const g of Object.values(TAG_GROUPS)) {
    const items: Array<{ short: string; value: any }> = []
    for (const f of g.fields) {
      const val = props.item.tags[f]
      if (val !== undefined && val !== null) {
        items.push({ short: FIELD_SHORT_LABELS[f] || f, value: val })
      }
    }
    if (items.length > 0) {
      result.push({ label: g.label, items })
    }
  }
  return result
})

function getLabel(key: string) {
  return TAG_LABELS[key] || key
}
</script>

<template>
  <el-dialog
    v-model="visible"
    :title="item.name"
    width="720px"
    destroy-on-close
    :append-to-body="true"
  >
    <div class="detail-layout">
      <!-- Preview -->
      <div v-if="previewSrc" class="detail-preview">
        <div v-if="isEffect" class="effect-previews">
          <div class="preview-frame">
            <div class="preview-label">普通视角</div>
            <img :src="previewSrc" :alt="item.name" />
          </div>
          <div v-if="effectGridSrc" class="preview-frame">
            <div class="preview-label">网格视角</div>
            <img :src="effectGridSrc" :alt="item.name + ' grid'" />
          </div>
        </div>
        <div v-else class="preview-frame">
          <img :src="previewSrc" :alt="item.name" />
        </div>
      </div>

      <!-- Metadata -->
      <div class="detail-meta">
        <!-- Tags grid -->
        <div class="meta-grid">
          <div
            v-for="[key, val] in visibleTagEntries"
            :key="key"
            class="meta-item"
          >
            <span class="meta-label">{{ getLabel(key) }}</span>
            <span class="meta-value">
              {{ Array.isArray(val) ? val.join(' · ') : val }}
            </span>
          </div>
          <!-- Grouped numeric fields -->
          <div
            v-for="group in activeGroups"
            :key="group.label"
            class="meta-item"
          >
            <span class="meta-label">{{ group.label }}</span>
            <span class="meta-value">
              {{ group.items.map(i => `${i.short}: ${i.value}`).join(' / ') }}
            </span>
          </div>
        </div>

        <!-- Resource path -->
        <div class="meta-path">
          <span class="path-label">资源路径</span>
          <div class="path-row">
            <code class="path-value">{{ item.resource_path }}</code>
            <button class="copy-btn" :class="{ copied }" @click="copyPath">
              <svg v-if="!copied" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              <span v-else class="copied-check">&#10003;</span>
            </button>
          </div>
        </div>

        <!-- Score -->
        <div v-if="item.relevance_score" class="meta-score">
          <span class="score-label">相关度</span>
          <div class="score-bar-track">
            <div
              class="score-bar-fill"
              :style="{ width: `${Math.min(item.relevance_score * 100, 100)}%` }"
            />
          </div>
          <span class="score-value">{{ (item.relevance_score * 100).toFixed(0) }}%</span>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
.detail-layout {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* --- Preview --- */
.detail-preview {
  display: flex;
  justify-content: center;
}

.effect-previews {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
}

.effect-previews .preview-frame {
  flex: 1;
  min-width: 200px;
  max-width: 320px;
}

.preview-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  text-align: center;
  margin-bottom: 6px;
}

.preview-frame {
  max-width: 400px;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--bg-root);
  border: 1px solid var(--border-subtle);
}

.preview-frame img {
  display: block;
  max-width: 100%;
  max-height: 380px;
  object-fit: contain;
}

/* --- Meta grid --- */
.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 2px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

.meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 14px;
  background: var(--bg-surface);
}

.meta-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.meta-value {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.4;
}

/* --- Resource path --- */
.meta-path {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.path-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.path-row {
  display: flex;
  align-items: stretch;
  gap: 0;
}

.path-value {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
  background: var(--bg-surface);
  padding: 8px 12px;
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
  border: 1px solid var(--border-subtle);
  border-right: none;
  word-break: break-all;
  flex: 1;
}

.copy-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  border: 1px solid var(--border-subtle);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: var(--bg-surface);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.copy-btn:hover {
  background: var(--bg-surface-hover);
  color: var(--text-primary);
}

.copy-btn.copied {
  color: #4ade80;
}

.copied-check {
  font-size: 14px;
  font-weight: 700;
}

/* --- Score bar --- */
.meta-score {
  display: flex;
  align-items: center;
  gap: 10px;
}

.score-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  white-space: nowrap;
}

.score-bar-track {
  flex: 1;
  height: 4px;
  border-radius: 2px;
  background: var(--bg-surface-hover);
  overflow: hidden;
}

.score-bar-fill {
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, var(--accent), #f0c060);
  transition: width 0.5s ease;
}

.score-value {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  color: var(--accent-text);
  min-width: 36px;
  text-align: right;
}
</style>
