// frontend/src/components/__tests__/AssetDetailModal.spec.ts
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { describe, beforeEach, afterEach, it, expect, vi } from 'vitest'
import AssetDetailModal from '../AssetDetailModal.vue'
import { useSearchStore } from '@/stores/searchStore'
import type { AssetItem } from '@/types'

vi.mock('@/api/search', () => ({
  searchAssets: vi.fn().mockResolvedValue({
    total: 0, page: 1, page_size: 60,
    parse_info: null, items: [], facets: {}, query_time_ms: 1,
  }),
  getTagDefinitions: vi.fn().mockResolvedValue([]),
}))

function makeItem(overrides: Partial<AssetItem> = {}): AssetItem {
  return {
    id: 1,
    name: 'hero_model',
    resource_path: '/resources/hero/model.fbx',
    thumbnail_path: 'hero.png',
    tags: {},
    relevance_score: 0.85,
    highlight: {},
    ...overrides,
  }
}

// A stub for el-dialog that renders the default slot and supports v-model
const ElDialogStub = {
  name: 'ElDialog',
  template: `<div class="el-dialog-stub"><slot name="header"></slot><slot></slot></div>`,
  props: ['modelValue', 'width', 'destroyOnClose', 'appendToBody'],
  emits: ['update:modelValue', 'close'],
}

// Store original clipboard descriptor
const originalClipboard = Object.getOwnPropertyDescriptor(navigator, 'clipboard')

describe('AssetDetailModal', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // Restore clipboard to a working mock for each test
    const clipboardMock = { writeText: vi.fn().mockResolvedValue(undefined) }
    Object.defineProperty(navigator, 'clipboard', {
      value: clipboardMock,
      configurable: true,
      writable: true,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    // Restore original clipboard descriptor
    if (originalClipboard) {
      Object.defineProperty(navigator, 'clipboard', originalClipboard)
    }
  })

  // 1. 复制路径
  it('复制路径', async () => {
    const store = useSearchStore()
    store.moduleType = 1

    const wrapper = mount(AssetDetailModal, {
      props: { item: makeItem(), modelValue: true },
      global: {
        stubs: { 'el-dialog': ElDialogStub },
      },
    })

    const copyBtn = wrapper.find('[data-testid="copy-path-btn"]')
    expect(copyBtn.exists()).toBe(true)

    await copyBtn.trigger('click')
    await flushPromises()

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('/resources/hero/model.fbx')
  })

  // 2. 复制 icon ID（仅 icon 模块）
  it('复制 icon ID（仅 icon 模块）', async () => {
    const store = useSearchStore()
    store.moduleType = 4  // icon module

    const wrapper = mount(AssetDetailModal, {
      props: {
        item: makeItem({ tags: { icon_id: 42001 } }),
        modelValue: true,
      },
      global: {
        stubs: { 'el-dialog': ElDialogStub },
      },
    })

    const copyIdBtn = wrapper.find('[data-testid="copy-id-btn"]')
    expect(copyIdBtn.exists()).toBe(true)

    await copyIdBtn.trigger('click')
    await flushPromises()

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('42001')
  })

  // 3. clipboard fallback（navigator.clipboard 不可用时）
  it('clipboard fallback（navigator.clipboard 不可用时）', async () => {
    // Disable clipboard API for this test
    Object.defineProperty(navigator, 'clipboard', {
      value: undefined,
      configurable: true,
      writable: true,
    })

    // jsdom may not have execCommand — define it so spyOn works
    if (!document.execCommand) {
      document.execCommand = () => false
    }
    const execCommandSpy = vi.spyOn(document, 'execCommand').mockReturnValue(true)

    const store = useSearchStore()
    store.moduleType = 1

    const wrapper = mount(AssetDetailModal, {
      props: { item: makeItem(), modelValue: true },
      global: {
        stubs: { 'el-dialog': ElDialogStub },
      },
    })

    const copyBtn = wrapper.find('[data-testid="copy-path-btn"]')
    expect(copyBtn.exists()).toBe(true)
    await copyBtn.trigger('click')
    await flushPromises()

    // fallbackCopy should be called — which calls execCommand('copy')
    expect(execCommandSpy).toHaveBeenCalledWith('copy')
  })

  // 4. ESC 关闭（via el-dialog emitting update:modelValue=false）
  it('ESC 关闭', async () => {
    const store = useSearchStore()
    store.moduleType = 1

    const wrapper = mount(AssetDetailModal, {
      props: { item: makeItem(), modelValue: true },
      global: {
        stubs: { 'el-dialog': ElDialogStub },
      },
    })

    // Simulate el-dialog's close behavior (ESC key or close button)
    // by finding the stub and emitting update:modelValue = false
    const dialog = wrapper.findComponent(ElDialogStub)
    await dialog.vm.$emit('update:modelValue', false)
    await flushPromises()

    // AssetDetailModal should propagate the close event
    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted![0]).toEqual([false])
  })

  // 5. 点遮罩关闭（close-on-click-modal default true）
  it('点遮罩关闭', async () => {
    const store = useSearchStore()
    store.moduleType = 1

    const wrapper = mount(AssetDetailModal, {
      props: { item: makeItem(), modelValue: true },
      global: {
        stubs: { 'el-dialog': ElDialogStub },
      },
    })

    // Simulate overlay click closing the dialog
    const dialog = wrapper.findComponent(ElDialogStub)
    await dialog.vm.$emit('update:modelValue', false)
    await flushPromises()

    const emitted = wrapper.emitted('update:modelValue')
    expect(emitted).toBeTruthy()
    expect(emitted![0]).toEqual([false])
  })
})
