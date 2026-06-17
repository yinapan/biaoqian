<script setup lang="ts">
import SearchPage from './views/SearchPage.vue'
</script>

<template>
  <SearchPage />
</template>

<style>
:root {
  /* --- Surface palette --- */
  --bg-root: #0c0d10;
  --bg-elevated: #141518;
  --bg-surface: #1a1b20;
  --bg-surface-hover: #22232a;
  --bg-overlay: rgba(10, 10, 14, 0.85);

  /* --- Accent --- */
  --accent: #e8a838;
  --accent-soft: rgba(232, 168, 56, 0.12);
  --accent-glow: rgba(232, 168, 56, 0.25);
  --accent-text: #f0c060;

  /* --- Text --- */
  --text-primary: #e8e6e1;
  --text-secondary: #908d85;
  --text-muted: #5c5a54;
  --text-on-accent: #0c0d10;

  /* --- Border --- */
  --border-subtle: rgba(255, 255, 255, 0.06);
  --border-light: rgba(255, 255, 255, 0.1);
  --border-accent: rgba(232, 168, 56, 0.3);

  /* --- Glass --- */
  --glass-bg: rgba(26, 27, 32, 0.6);
  --glass-border: rgba(255, 255, 255, 0.08);
  --glass-blur: 20px;

  /* --- Spacing --- */
  --header-height: 72px;
  --sidebar-width: 280px;

  /* --- Type --- */
  --font-sans: 'Noto Sans SC', system-ui, -apple-system, sans-serif;
  --font-mono: 'Space Mono', 'SF Mono', monospace;

  /* --- Radius --- */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;

  /* --- Shadows --- */
  --shadow-card: 0 2px 12px rgba(0, 0, 0, 0.4), 0 0 0 1px var(--border-subtle);
  --shadow-card-hover: 0 8px 32px rgba(0, 0, 0, 0.5), 0 0 0 1px var(--border-light);
  --shadow-glow: 0 0 20px var(--accent-glow);

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
  box-shadow: 0 0 0 1px var(--accent) inset, var(--shadow-glow) !important;
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
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 0 0 0 var(--accent-glow); }
  50% { box-shadow: 0 0 16px 4px var(--accent-glow); }
}
</style>
