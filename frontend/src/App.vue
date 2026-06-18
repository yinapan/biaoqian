<script setup lang="ts">
import SearchPage from './views/SearchPage.vue'
</script>

<template>
  <SearchPage />
</template>

<style>
:root {
  --bg-root: #101418;
  --bg-elevated: #171c22;
  --bg-surface: #1d232b;
  --bg-surface-hover: #26303a;
  --bg-overlay: rgba(5, 8, 12, 0.72);

  --accent: #4f9caf;
  --accent-strong: #66b6c8;
  --accent-soft: rgba(79, 156, 175, 0.14);
  --accent-text: #8fcddd;
  --warn-soft: rgba(202, 138, 4, 0.14);
  --warn-text: #e0b45e;

  --text-primary: #e4e9ee;
  --text-secondary: #a7b1bd;
  --text-muted: #6f7a86;
  --text-on-accent: #ffffff;

  --border-subtle: rgba(226, 232, 240, 0.08);
  --border-light: rgba(226, 232, 240, 0.16);
  --border-accent: rgba(79, 156, 175, 0.34);

  /* --- Spacing --- */
  --header-height: 72px;
  --sidebar-width: 304px;

  /* --- Type --- */
  --font-sans: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', system-ui, sans-serif;
  --font-mono: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;

  /* --- Radius: tight, not bubbly --- */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;

  /* --- Shadows: no glow --- */
  --shadow-card: 0 1px 2px rgba(0, 0, 0, 0.28);
  --shadow-card-hover: 0 10px 24px rgba(0, 0, 0, 0.36);

  /* --- Element Plus theme overrides --- */
  --el-color-primary: var(--accent);
  --el-bg-color: var(--bg-surface);
  --el-bg-color-overlay: var(--bg-elevated);
  --el-text-color-primary: var(--text-primary);
  --el-text-color-regular: var(--text-secondary);
  --el-text-color-secondary: var(--text-muted);
  --el-border-color: var(--border-subtle);
  --el-border-color-light: var(--border-subtle);
  --el-border-color-lighter: var(--border-subtle);
  --el-fill-color-blank: var(--bg-surface);
  --el-fill-color-light: var(--bg-surface-hover);
  --el-mask-color: var(--bg-overlay);
}

*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
}

html,
body {
  height: 100%;
  background: var(--bg-root);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#app {
  height: 100%;
}

/* --- Scrollbar --- */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(226, 232, 240, 0.14);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(226, 232, 240, 0.24);
}

/* --- Element Plus overrides --- */
.el-dialog {
  --el-dialog-bg-color: var(--bg-elevated) !important;
  --el-dialog-border-radius: var(--radius-lg) !important;
  border: 1px solid var(--border-subtle) !important;
}
.el-dialog__header {
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 16px;
}
.el-dialog__title {
  color: var(--text-primary) !important;
}

.el-button--primary {
  --el-button-bg-color: var(--accent);
  --el-button-border-color: var(--accent);
  --el-button-hover-bg-color: var(--accent-strong);
  --el-button-hover-border-color: var(--accent-strong);
}

.el-descriptions {
  --el-descriptions-table-border: var(--border-subtle);
}
.el-descriptions__body .el-descriptions__label {
  background: var(--bg-surface) !important;
  color: var(--text-muted) !important;
}
.el-descriptions__body .el-descriptions__content {
  background: var(--bg-elevated) !important;
  color: var(--text-primary) !important;
}

.el-input__wrapper {
  background: var(--bg-surface) !important;
  box-shadow: 0 0 0 1px var(--border-subtle) inset !important;
}
.el-input__wrapper:hover {
  box-shadow: 0 0 0 1px var(--border-light) inset !important;
}
.el-input__wrapper.is-focus {
  box-shadow: 0 0 0 1px var(--accent) inset !important;
}
.el-input__inner {
  color: var(--text-primary) !important;
}
.el-input__inner::placeholder {
  color: var(--text-muted) !important;
}

.el-checkbox__label {
  color: var(--text-secondary) !important;
}
.el-checkbox__input.is-checked + .el-checkbox__label {
  color: var(--accent-text) !important;
}

.el-pagination {
  --el-pagination-bg-color: transparent;
  --el-pagination-button-bg-color: var(--bg-surface);
  --el-pagination-hover-color: var(--accent);
}
.el-pagination button,
.el-pagination .el-pager li {
  background: var(--bg-surface) !important;
  color: var(--text-secondary) !important;
  border: 1px solid var(--border-subtle) !important;
}
.el-pagination .el-pager li.is-active {
  background: var(--accent) !important;
  color: var(--text-on-accent) !important;
  border-color: var(--accent) !important;
}

.el-empty__description p {
  color: var(--text-muted) !important;
}

.el-slider__runway {
  background: #2a3440 !important;
}

.el-switch.is-checked .el-switch__core {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
}

/* --- Keyframes --- */
@keyframes fadeInUp {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
</style>
