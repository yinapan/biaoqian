<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AssetItem } from '@/types'

const props = defineProps<{
  item: AssetItem
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
}>()

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

const previewSrc = computed(() => {
  if (!props.item.thumbnail_path) return ''
  return `/static/previews/${props.item.thumbnail_path}`
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
}

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
        <div class="preview-frame">
          <img :src="previewSrc" :alt="item.name" />
        </div>
      </div>

      <!-- Metadata -->
      <div class="detail-meta">
        <!-- Tags grid -->
        <div class="meta-grid">
          <div
            v-for="[key, val] in tagEntries"
            :key="key"
            class="meta-item"
          >
            <span class="meta-label">{{ getLabel(key) }}</span>
            <span class="meta-value">
              {{ Array.isArray(val) ? val.join(' · ') : val }}
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
