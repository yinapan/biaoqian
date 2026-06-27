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
const iconIdCopied = ref(false)

const isIcon = computed(() => store.moduleType === 4)
const isEffect = computed(() => store.moduleType === 2)
const isModel = computed(() => store.moduleType === 1)
const isAnimator = computed(() => store.moduleType === 3)

const MODULE_BADGE: Record<number, { label: string; tone: string }> = {
  1: { label: 'MODEL', tone: 'tone-model' },
  2: { label: 'EFFECT', tone: 'tone-effect' },
  3: { label: 'ANIMATOR', tone: 'tone-animator' },
  4: { label: 'ICON', tone: 'tone-icon' },
}
const badge = computed(() => MODULE_BADGE[store.moduleType] ?? { label: 'ASSET', tone: 'tone-default' })

const dialogWidth = computed(() => {
  if (isEffect.value || isAnimator.value) return 'min(2400px, 92vw)'
  if (isIcon.value) return 'min(1000px, 90vw)'
  return 'min(1000px, 90vw)'
})

const previewSrc = computed(() => {
  if (!props.item.thumbnail_path) return ''
  if (isEffect.value) return `/data/gifs/${props.item.thumbnail_path}`
  if (isIcon.value) return `/data/icons/${props.item.thumbnail_path}`
  if (isModel.value) return `/static/previews/model/${props.item.thumbnail_path}`
  if (isAnimator.value) return `/static/previews/animator/${props.item.thumbnail_path}`
  return `/static/previews/${props.item.thumbnail_path}`
})

const effectGridSrc = computed(() => {
  if (!isEffect.value || !props.item.thumbnail_path) return ''
  const gridName = props.item.thumbnail_path.replace('.gif', '_grid.gif')
  return `/data/gifs/${gridName}`
})

const animatorLeftSrc = computed(() => {
  if (!isAnimator.value) return ''
  const leftPath = props.item.tags?.gif_left_path
  if (!leftPath) return ''
  return `/static/previews/animator/${leftPath}`
})

const previewLabelLeft = computed(() => {
  if (isEffect.value) return '普通视角'
  if (isAnimator.value) return '前视角'
  return '原始'
})

const previewLabelRight = computed(() => {
  if (isEffect.value) return '网格视角'
  if (isAnimator.value) return '左视角'
  if (isIcon.value) return '放大查看'
  return ''
})

const hasPairedPreviews = computed(() => {
  if (isEffect.value) return Boolean(effectGridSrc.value)
  if (isAnimator.value) return Boolean(animatorLeftSrc.value)
  if (isIcon.value) return true
  return false
})

const tagEntries = computed(() => Object.entries(props.item.tags))
const svnEntries = computed(() => {
  const svn = props.item.tags?.__svn
  if (!svn || typeof svn !== 'object' || Array.isArray(svn)) return []
  return Object.entries(svn)
    .filter(([, val]) => val !== undefined && val !== null && String(val) !== '')
    .map(([key, val]) => ({
      key,
      label: SVN_LABELS[key] || key,
      value: String(val),
    }))
})

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
  predefined: '类别',
  semantic: '语义',
  icon_id: '图标ID',
  width_px: '宽 (px)',
  height_px: '高 (px)',
  framed: '是否分帧',
  related_items: '相关物品',
  tag_source: '标签来源',
  layout: '版面布局',
  resource_type: '资源类型',
  special_system: '特殊系统',
  school: '门派',
  weapon_type: '武器类型',
  common_action: '通用动作分类',
  mount_type: '骑乘类型',
  qinggong_type: '轻功类型',
  core_action: '核心动作',
  file_type: '文件类型',
  ai_tags: 'AI分析标签',
}

const TAG_GROUPS: Record<string, { label: string; fields: string[]; unit?: string }> = {
  dimensions: { label: '尺寸 (cm)', fields: ['length_cm', 'width_cm', 'height_cm'], unit: 'cm' },
  dimensions_px: { label: '尺寸 (px)', fields: ['width_px', 'height_px'] },
  camera: { label: '相机参数', fields: ['camera_distance', 'camera_scale'] },
  coverage: { label: '画面占比', fields: ['area_ratio', 'span_max'] },
}

const GROUPED_FIELDS = new Set(Object.values(TAG_GROUPS).flatMap(g => g.fields))

const HIDDEN_FIELDS = new Set([
  'gif_duration_sec',
  'focus_offset',
  'center_x',
  'center_y',
  'clipped',
  'fit_attempts',
  'fit_stop_reason',
  'source_name',
  'size_bytes',
  'scope_size',
  'gif_front_path',
  'gif_left_path',
  'layout',
  '__svn',
  '__source_version',
])

const DEDICATED_FIELDS = new Set(['icon_id'])

const SVN_LABELS: Record<string, string> = {
  path: 'SVN 路径',
  url: 'SVN 地址',
  repo: '仓库',
  repository: '仓库',
  revision: '版本号',
  rev: '版本号',
  commit: '提交号',
  author: '提交人',
  date: '提交时间',
  branch: '分支',
}

const FIELD_SHORT_LABELS: Record<string, string> = {
  length_cm: '长', width_cm: '宽', height_cm: '高',
  camera_distance: '距离', camera_scale: '缩放',
  area_ratio: '面积', span_max: '跨度',
  width_px: '宽', height_px: '高',
}

const visibleTagEntries = computed(() =>
  tagEntries.value.filter(([key, val]) =>
    !GROUPED_FIELDS.has(key) && !HIDDEN_FIELDS.has(key) && !DEDICATED_FIELDS.has(key) &&
    !(key === 'framed' && val !== true)
  )
)

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

function formatValue(key: string, val: any): string {
  if (typeof val === 'boolean') return val ? '是' : '否'
  if (Array.isArray(val)) return val.join(' · ')
  if (val && typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

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

function copyIconId() {
  const text = String(props.item.tags?.icon_id ?? props.item.name)
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).catch(() => fallbackCopy(text))
  } else {
    fallbackCopy(text)
  }
  iconIdCopied.value = true
  setTimeout(() => (iconIdCopied.value = false), 1500)
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
</script>

<template>
  <el-dialog
    v-model="visible"
    :width="dialogWidth"
    destroy-on-close
    :append-to-body="true"
    class="asset-detail-dialog"
  >
    <template #header>
      <div class="dialog-header">
        <span class="module-badge" :class="badge.tone">{{ badge.label }}</span>
        <h2 class="asset-title" :title="item.name">{{ item.name }}</h2>
      </div>
    </template>

    <div class="detail-grid">
      <!-- Preview stage -->
      <section class="preview-stage" :class="{ 'is-paired': hasPairedPreviews }">
        <div v-if="previewSrc" class="preview-canvas">
          <div v-if="isIcon" class="icon-preview-pair">
            <div class="preview-frame is-icon-original">
              <div class="preview-label">{{ previewLabelLeft }}</div>
              <img :src="previewSrc" :alt="item.name" loading="eager" fetchpriority="high" />
            </div>
            <div class="preview-frame is-icon-zoom">
              <div class="preview-label">{{ previewLabelRight }}</div>
              <img :src="previewSrc" :alt="item.name + ' zoom'" loading="eager" />
            </div>
          </div>

          <div v-else-if="isEffect || isAnimator" class="effect-previews">
            <div class="preview-frame">
              <div class="preview-label">{{ previewLabelLeft }}</div>
              <img :src="previewSrc" :alt="item.name" loading="eager" fetchpriority="high" />
            </div>
            <div v-if="hasPairedPreviews" class="preview-frame">
              <div class="preview-label">{{ previewLabelRight }}</div>
              <img
                v-if="isEffect"
                :src="effectGridSrc"
                :alt="item.name + ' grid'"
                loading="eager"
              />
              <img
                v-else
                :src="animatorLeftSrc"
                :alt="item.name + ' left'"
                loading="eager"
              />
            </div>
          </div>

          <div v-else class="preview-frame is-single">
            <img :src="previewSrc" :alt="item.name" loading="eager" fetchpriority="high" />
          </div>
        </div>

        <div v-if="item.relevance_score" class="stage-score">
          <span class="score-label">相关度</span>
          <div class="score-bar-track">
            <div
              class="score-bar-fill"
              :style="{ width: `${Math.min(item.relevance_score * 100, 100)}%` }"
            />
          </div>
          <span class="score-value">{{ (item.relevance_score * 100).toFixed(0) }}%</span>
        </div>
      </section>

      <!-- Metadata column -->
      <aside class="meta-column">
        <div class="meta-grid">
          <div
            v-for="[key, val] in visibleTagEntries"
            :key="key"
            class="meta-item"
          >
            <span class="meta-label">{{ getLabel(key) }}</span>
            <span class="meta-value" :class="{ 'is-code': typeof val === 'number' || key.endsWith('_id') }">
              {{ formatValue(key, val) }}
            </span>
          </div>
          <div
            v-for="group in activeGroups"
            :key="group.label"
            class="meta-item"
          >
            <span class="meta-label">{{ group.label }}</span>
            <span class="meta-value is-code">
              {{ group.items.map(i => `${i.short} ${i.value}`).join(' · ') }}
            </span>
          </div>
        </div>

        <div v-if="isIcon" class="meta-card icon-id-section">
          <span class="card-label">Icon ID</span>
          <div class="icon-id-row">
            <div class="icon-id-display">
              <span class="icon-id-badge">ID</span>
              <code class="icon-id-code">{{ item.tags?.icon_id ?? item.name }}</code>
            </div>
            <button class="id-copy-action" :class="{ copied: iconIdCopied }" @click="copyIconId()">
              <svg v-if="!iconIdCopied" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="8" y="8" width="14" height="14" rx="2.5"/><path d="M4 16H3a2 2 0 0 1-2-2V3a2 2 0 0 1 2-2h11a2 2 0 0 1 2 2v1"/></svg>
              <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              <span class="id-copy-text" :class="{ visible: iconIdCopied }">已复制</span>
            </button>
          </div>
        </div>

        <div class="meta-card path-section">
          <span class="card-label">资源路径</span>
          <div class="path-row">
            <code class="path-value">{{ item.resource_path }}</code>
            <button class="copy-btn" :class="{ copied }" @click="copyPath" :title="copied ? '已复制' : '复制路径'">
              <svg v-if="!copied" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            </button>
          </div>
        </div>

        <div v-if="svnEntries.length" class="meta-card svn-section">
          <span class="card-label">SVN 信息</span>
          <div class="svn-grid">
            <div v-for="entry in svnEntries" :key="entry.key" class="svn-item">
              <span class="svn-label">{{ entry.label }}</span>
              <code class="svn-value" :title="entry.value">{{ entry.value }}</code>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </el-dialog>
</template>

<style scoped>
/* ===== Header ===== */
.dialog-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-right: 24px;
  min-width: 0;
}

.module-badge {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: 3px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.14em;
  border: 1px solid currentColor;
  line-height: 1.4;
}
.module-badge.tone-model {
  color: #c4a45e;
  background: rgba(196, 164, 94, 0.08);
}
.module-badge.tone-effect {
  color: #d98a7a;
  background: rgba(217, 138, 122, 0.08);
}
.module-badge.tone-animator {
  color: #a8b5d8;
  background: rgba(168, 181, 216, 0.08);
}
.module-badge.tone-icon {
  color: var(--accent-text);
  background: var(--accent-soft);
}
.module-badge.tone-default {
  color: var(--text-muted);
  background: var(--bg-surface);
}

.asset-title {
  flex: 1;
  min-width: 0;
  font-family: var(--font-sans);
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ===== Detail grid: preview | meta ===== */
.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 20px;
  max-height: calc(90vh - 80px);
}

.meta-column {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
  scrollbar-width: thin;
}

/* ===== Preview stage ===== */
.preview-stage {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  min-height: 0;
}

.preview-canvas {
  position: relative;
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px;
  border-radius: var(--radius-lg);
  background:
    radial-gradient(circle at 50% 35%, rgba(79, 156, 175, 0.06), transparent 65%),
    linear-gradient(180deg, var(--bg-root) 0%, #0c1014 100%);
  border: 1px solid var(--border-subtle);
  overflow: hidden;
}

.preview-stage.is-paired .preview-canvas {
  padding: 8px;
}

/* Single preview (model) — maximize within available height */
.preview-frame.is-single {
  display: flex;
  align-items: center;
  justify-content: center;
  max-width: 100%;
  max-height: 100%;
}
.preview-frame.is-single img {
  display: block;
  width: auto;
  height: auto;
  max-width: 100%;
  max-height: calc(88vh - 130px);
  border-radius: var(--radius-sm);
}

/* Paired previews (effect, animator, icon) */
.effect-previews,
.icon-preview-pair {
  display: flex;
  gap: 10px;
  justify-content: center;
  align-items: flex-start;
  flex-wrap: nowrap;
  width: max-content;
  max-width: 100%;
  margin: 0 auto;
}

.effect-previews .preview-frame,
.icon-preview-pair .preview-frame {
  flex: 0 1 auto;
  min-width: 0;
  max-width: calc((100% - 10px) / 2);
  display: flex;
  flex-direction: column;
  align-items: center;
  background: rgba(13, 17, 22, 0.6);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  backdrop-filter: blur(4px);
}

.preview-frame img {
  display: block;
  width: auto;
  height: auto;
  max-width: 100%;
  max-height: calc(88vh - 150px);
}

.icon-preview-pair .preview-frame {
  max-width: min(100%, 360px);
}

.is-icon-zoom img {
  width: 240px;
  height: 240px;
  max-width: 100%;
  max-height: 240px;
  object-fit: contain;
  image-rendering: auto;
}

.preview-label {
  align-self: stretch;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  text-align: center;
  padding: 5px 8px 4px;
  border-bottom: 1px solid var(--border-subtle);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.02), transparent);
}

/* ===== Stage score (under preview) ===== */
.stage-score {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 4px;
}
.score-label {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--text-muted);
  white-space: nowrap;
}
.score-bar-track {
  flex: 1;
  height: 3px;
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

/* ===== Meta grid ===== */
.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1px;
  background: var(--border-subtle);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.meta-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 9px 12px;
  background: var(--bg-elevated);
  transition: background 0.15s ease;
}
.meta-item:hover {
  background: var(--bg-surface);
}
.meta-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
}
.meta-value {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.45;
  word-break: break-word;
}
.meta-value.is-code {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
}

/* ===== Meta cards (path, icon id) ===== */
.meta-card {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 12px 14px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
}
.card-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
}

.svn-section {
  gap: 10px;
}
.svn-grid {
  display: grid;
  gap: 8px;
}
.svn-item {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 8px;
  align-items: baseline;
}
.svn-label {
  color: var(--text-muted);
  font-size: 11px;
}
.svn-value {
  min-width: 0;
  padding: 5px 7px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  background: var(--bg-root);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 11px;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.path-row {
  display: flex;
  align-items: stretch;
  gap: 0;
}
.path-value {
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: var(--text-secondary);
  background: var(--bg-root);
  padding: 8px 12px;
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
  border: 1px solid var(--border-subtle);
  border-right: none;
  word-break: break-all;
  flex: 1;
  min-width: 0;
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
  background: var(--accent-soft);
  color: var(--accent-text);
  border-color: var(--border-accent);
}
.copy-btn.copied {
  color: #4ade80;
  border-color: rgba(34, 197, 94, 0.3);
  background: rgba(22, 163, 74, 0.12);
}

/* ===== Icon ID ===== */
.icon-id-row {
  display: flex;
  align-items: stretch;
  gap: 0;
}
.icon-id-display {
  display: flex;
  align-items: stretch;
  flex: 1;
  min-width: 0;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
  overflow: hidden;
  background: var(--bg-root);
}
.icon-id-badge {
  display: flex;
  align-items: center;
  padding: 0 10px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--accent-text);
  background: var(--accent-soft);
  border-right: 1px solid var(--border-subtle);
  flex-shrink: 0;
}
.icon-id-code {
  display: flex;
  align-items: center;
  font-family: var(--font-mono);
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  padding: 8px 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.id-copy-action {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-width: 44px;
  padding: 0 12px;
  border: 1px solid var(--border-subtle);
  border-left: none;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: var(--bg-surface);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}
.id-copy-action:hover {
  background: var(--accent-soft);
  color: var(--accent-text);
  border-color: var(--border-accent);
}
.id-copy-action.copied {
  background: rgba(22, 163, 74, 0.14);
  color: #4ade80;
  border-color: rgba(34, 197, 94, 0.3);
  min-width: 72px;
}
.id-copy-text {
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  opacity: 0;
  width: 0;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.id-copy-text.visible {
  opacity: 1;
  width: 32px;
}

/* ===== Responsive: stack on narrow viewports ===== */
@media (max-width: 880px) {
  .detail-grid {
    grid-template-columns: minmax(0, 1fr);
    max-height: none;
  }
  .meta-column {
    overflow-y: visible;
  }
  .preview-frame img,
  .preview-frame.is-single img {
    max-height: calc(72vh - 120px);
  }
}
</style>

<style>
/* Element Plus dialog overrides for asset detail */
.asset-detail-dialog .el-dialog {
  background: var(--bg-elevated) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: var(--radius-lg) !important;
  display: flex;
  flex-direction: column;
  max-height: min(92vh, 1080px);
  overflow: hidden;
}
.asset-detail-dialog .el-dialog__header {
  margin-right: 0 !important;
  padding: 14px 20px !important;
  border-bottom: 1px solid var(--border-subtle);
}
.asset-detail-dialog .el-dialog__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
  padding: 18px 20px 20px !important;
}
.asset-detail-dialog .el-dialog__headerbtn {
  top: 16px !important;
  right: 16px !important;
}
</style>
