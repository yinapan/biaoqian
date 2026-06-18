<script setup lang="ts">
import SearchPage from './views/SearchPage.vue'
</script>

<template>
  <SearchPage />
</template>

<style>
:root {
  /* --- Surface palette: slightly warm neutral, not sci-fi black --- */
  --bg-root: #111214;
  --bg-elevated: #191a1e;
  --bg-surface: #1f2024;
  --bg-surface-hover: #27282d;
  --bg-overlay: rgba(10, 10, 14, 0.85);

  /* --- Accent: muted warm tone, not neon gold --- */
  --accent: #c49a5c;
  --accent-soft: rgba(196, 154, 92, 0.10);
  --accent-text: #d4b07a;

  /* --- Text: warm off-white for long sessions --- */
  --text-primary: #d8d6d0;
  --text-secondary: #8a877f;
  --text-muted: #555349;
  --text-on-accent: #111214;

  /* --- Border: structural only --- */
  --border-subtle: rgba(255, 255, 255, 0.06);
  --border-light: rgba(255, 255, 255, 0.10);
  --border-accent: rgba(196, 154, 92, 0.25);

  /* --- Spacing --- */
  --header-height: 56px;
  --sidebar-width: 264px;

  /* --- Type --- */
  --font-sans: 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', system-ui, sans-serif;
  --font-mono: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;

  /* --- Radius: tight, not bubbly --- */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 10px;

  /* --- Shadows: no glow --- */
  --shadow-card: 0 1px 3px rgba(0, 0, 0, 0.3);
  --shadow-card-hover: 0 2px 8px rgba(0, 0, 0, 0.4);

  /* --- Element Plus dark overrides --- */
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
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.18);
}

/* --- Element Plus overrides for dark theme --- */
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
  background: var(--bg-surface-hover) !important;
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
