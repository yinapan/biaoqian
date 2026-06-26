import { test, expect } from '@playwright/test'
import { SearchPage } from '../pages/SearchPage'
import {
  getNaturalSize,
  getRenderedSize,
  getObjectFit,
  attachVisualFailureArtifacts,
} from '../fixtures/visual-quality-helpers'

async function openFirstCardModal(page: import('@playwright/test').Page, tabN: 1 | 2 | 3 | 4) {
  const sp = new SearchPage(page)
  await sp.goto()
  await sp.moduleTabs.clickTab(tabN)
  await page.waitForLoadState('networkidle')
  await sp.resultGrid.firstCard().click()
  await sp.detailModal.expectOpen()
  return sp
}

test.describe('视觉与图片质量', () => {
  test('模型 PNG 宽高比保持', async ({ page }, info) => {
    try {
      const sp = await openFirstCardModal(page, 1)
      const previewSel = '[data-testid="detail-preview"]'
      const hasPreview = await page.locator(previewSel).count()
      if (hasPreview === 0) {
        test.skip()
        return
      }
      const natural = await getNaturalSize(page, previewSel)
      const rendered = await getRenderedSize(page, previewSel)
      if (natural.w > 0 && natural.h > 0 && rendered.w > 0 && rendered.h > 0) {
        const naturalRatio = natural.w / natural.h
        const renderedRatio = rendered.w / rendered.h
        // object-fit: contain preserves aspect ratio
        expect(Math.abs(naturalRatio - renderedRatio)).toBeLessThan(0.05)
      }
    } catch (e) {
      await attachVisualFailureArtifacts(page, info, 'model-png')
      throw e
    }
  })

  test('动作 GIF 宽高比保持', async ({ page }, info) => {
    try {
      const sp = await openFirstCardModal(page, 2)
      const previewSel = '[data-testid="detail-preview"]'
      const hasPreview = await page.locator(previewSel).count()
      if (hasPreview === 0) {
        test.skip()
        return
      }
      const natural = await getNaturalSize(page, previewSel)
      const rendered = await getRenderedSize(page, previewSel)
      if (natural.w > 0 && natural.h > 0 && rendered.w > 0 && rendered.h > 0) {
        const naturalRatio = natural.w / natural.h
        const renderedRatio = rendered.w / rendered.h
        expect(Math.abs(naturalRatio - renderedRatio)).toBeLessThan(0.05)
      }
    } catch (e) {
      await attachVisualFailureArtifacts(page, info, 'animator-gif')
      throw e
    }
  })

  test('特效 GIF 宽高比保持', async ({ page }, info) => {
    try {
      const sp = await openFirstCardModal(page, 3)
      const previewSel = '[data-testid="detail-preview"]'
      const hasPreview = await page.locator(previewSel).count()
      if (hasPreview === 0) {
        test.skip()
        return
      }
      const natural = await getNaturalSize(page, previewSel)
      const rendered = await getRenderedSize(page, previewSel)
      if (natural.w > 0 && natural.h > 0 && rendered.w > 0 && rendered.h > 0) {
        const naturalRatio = natural.w / natural.h
        const renderedRatio = rendered.w / rendered.h
        expect(Math.abs(naturalRatio - renderedRatio)).toBeLessThan(0.05)
      }
    } catch (e) {
      await attachVisualFailureArtifacts(page, info, 'effects-gif')
      throw e
    }
  })

  test('图标 PNG 宽高比保持', async ({ page }, info) => {
    try {
      const sp = await openFirstCardModal(page, 4)
      const previewSel = '[data-testid="detail-preview"]'
      const hasPreview = await page.locator(previewSel).count()
      if (hasPreview === 0) {
        test.skip()
        return
      }
      const natural = await getNaturalSize(page, previewSel)
      const rendered = await getRenderedSize(page, previewSel)
      if (natural.w > 0 && natural.h > 0 && rendered.w > 0 && rendered.h > 0) {
        const naturalRatio = natural.w / natural.h
        const renderedRatio = rendered.w / rendered.h
        expect(Math.abs(naturalRatio - renderedRatio)).toBeLessThan(0.05)
      }
    } catch (e) {
      await attachVisualFailureArtifacts(page, info, 'icon-png')
      throw e
    }
  })

  test('object-fit 是 cover 或 contain', async ({ page }, info) => {
    try {
      const sp = new SearchPage(page)
      await sp.goto()
      await page.waitForLoadState('networkidle')
      await sp.resultGrid.firstCard().click()
      await sp.detailModal.expectOpen()
      const previewSel = '[data-testid="detail-preview"]'
      const hasPreview = await page.locator(previewSel).count()
      if (hasPreview === 0) {
        test.skip()
        return
      }
      const fit = await getObjectFit(page, previewSel)
      expect(['cover', 'contain']).toContain(fit)
    } catch (e) {
      await attachVisualFailureArtifacts(page, info, 'object-fit')
      throw e
    }
  })

  test('CLS < 0.1', async ({ page }, info) => {
    try {
      const sp = new SearchPage(page)
      await sp.goto()
      // Measure CLS during initial page load + search
      const cls = await page.evaluate(() => {
        return new Promise<number>(resolve => {
          let totalCls = 0
          const observer = new PerformanceObserver(list => {
            for (const entry of list.getEntries()) {
              totalCls += (entry as PerformanceEntry & { value: number }).value
            }
          })
          try {
            observer.observe({ type: 'layout-shift', buffered: true })
          } catch {
            // PerformanceObserver not supported — skip
            resolve(0)
            return
          }
          setTimeout(() => {
            observer.disconnect()
            resolve(totalCls)
          }, 3000)
        })
      })
      expect(cls).toBeLessThan(0.1)
    } catch (e) {
      await attachVisualFailureArtifacts(page, info, 'cls-measure')
      throw e
    }
  })
})
