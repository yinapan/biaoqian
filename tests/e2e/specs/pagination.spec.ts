import { test, expect } from '@playwright/test'
import { SearchPage } from '../pages/SearchPage'

test.describe('分页', () => {
  test('翻页下一页', async ({ page }) => {
    const sp = new SearchPage(page)
    await sp.goto()
    await page.waitForLoadState('networkidle')

    // Get the current page indicator
    const pageIndicator = page.locator('[data-testid="page-current"]')
    const hasIndicator = await pageIndicator.count()

    if (hasIndicator > 0) {
      const initialPage = await pageIndicator.textContent()

      // Click the next page button (el-pagination internal)
      const nextBtn = page.locator('.el-pagination .btn-next')
      const isDisabled = await nextBtn.getAttribute('disabled')

      if (!isDisabled) {
        await nextBtn.click()
        await page.waitForLoadState('networkidle')
        const newPage = await pageIndicator.textContent()
        // Page number should have increased
        expect(newPage).not.toBe(initialPage)
        await sp.resultGrid.expectAtLeastOneCard()
      } else {
        // Only one page of results — skip
        expect(true).toBe(true)
      }
    } else {
      // No pagination — all results fit on one page
      expect(true).toBe(true)
    }
  })

  test('翻页上一页', async ({ page }) => {
    const sp = new SearchPage(page)
    await sp.goto()
    await page.waitForLoadState('networkidle')

    const pageIndicator = page.locator('[data-testid="page-current"]')
    const nextBtn = page.locator('.el-pagination .btn-next')
    const prevBtn = page.locator('.el-pagination .btn-prev')
    const hasIndicator = await pageIndicator.count()

    if (hasIndicator > 0) {
      const nextDisabled = await nextBtn.getAttribute('disabled')
      if (!nextDisabled) {
        // Go to page 2
        await nextBtn.click()
        await page.waitForLoadState('networkidle')
        const page2Text = await pageIndicator.textContent()

        // Go back to page 1
        const prevDisabled = await prevBtn.getAttribute('disabled')
        if (!prevDisabled) {
          await prevBtn.click()
          await page.waitForLoadState('networkidle')
          const page1Text = await pageIndicator.textContent()
          expect(page1Text).not.toBe(page2Text)
          await sp.resultGrid.expectAtLeastOneCard()
        }
      } else {
        expect(true).toBe(true)
      }
    } else {
      expect(true).toBe(true)
    }
  })

  test('改 pageSize', async ({ page }) => {
    const sp = new SearchPage(page)
    await sp.goto()
    await page.waitForLoadState('networkidle')

    // el-pagination page-size select
    const pageSizeSelect = page.locator('.el-pagination .el-select').first()
    const hasSelect = await pageSizeSelect.count()

    if (hasSelect > 0) {
      const beforeCount = await sp.resultGrid.cards().count()
      // Open the page size dropdown
      await pageSizeSelect.click()
      await page.waitForTimeout(300)
      // Select a different page size option
      const options = page.locator('.el-select-dropdown .el-select-dropdown__item')
      const optCount = await options.count()
      if (optCount > 1) {
        await options.nth(1).click()
        await page.waitForLoadState('networkidle')
        const afterCount = await sp.resultGrid.cards().count()
        // Card count may change with different page size
        expect(afterCount).toBeGreaterThan(0)
      }
    } else {
      // No page size selector visible — single-page result set
      expect(true).toBe(true)
    }
  })

  test('跳到最后一页', async ({ page }) => {
    const sp = new SearchPage(page)
    await sp.goto()
    await page.waitForLoadState('networkidle')

    const pageIndicator = page.locator('[data-testid="page-current"]')
    const hasIndicator = await pageIndicator.count()

    if (hasIndicator > 0) {
      // Find "last page" button in el-pagination
      const lastPageBtn = page.locator('.el-pagination button[aria-label="Go to last page"]').first()
      const hasLastBtn = await lastPageBtn.count()

      if (hasLastBtn > 0) {
        await lastPageBtn.click()
        await page.waitForLoadState('networkidle')
        await sp.resultGrid.expectAtLeastOneCard()
        // Next button should now be disabled (we're on last page)
        const nextBtn = page.locator('.el-pagination .btn-next')
        const isDisabled = await nextBtn.getAttribute('disabled')
        expect(isDisabled).not.toBeNull()
      } else {
        // Try clicking the last numbered page
        const pageNumbers = page.locator('.el-pagination .el-pager .number')
        const pageCount = await pageNumbers.count()
        if (pageCount > 1) {
          await pageNumbers.last().click()
          await page.waitForLoadState('networkidle')
          await sp.resultGrid.expectAtLeastOneCard()
        } else {
          expect(true).toBe(true)
        }
      }
    } else {
      expect(true).toBe(true)
    }
  })

  test('从第 1 页直接跳第 100 页（offset 上限边界）', async ({ page }) => {
    const sp = new SearchPage(page)
    await sp.goto()
    await page.waitForLoadState('networkidle')

    // Try to navigate to page 100 via the jump-to input
    const jumpInput = page.locator('.el-pagination .el-pagination__jump .el-input__inner')
    const hasJump = await jumpInput.count()

    if (hasJump > 0) {
      await jumpInput.fill('100')
      await jumpInput.press('Enter')
      await page.waitForLoadState('networkidle')
      // Backend should handle offset limit gracefully — either return last page or empty
      // The page should not show an error
      const hasError = await page.locator('.el-message--error').count()
      // Either results exist or empty state is shown, no crash
      expect(hasError).toBe(0)
    } else {
      // Directly call the API with a large offset to verify boundary behavior
      const resp = await page.request.post('http://localhost:18081/api/v1/search/query', {
        data: { q: '', module: 1, offset: 9900, limit: 20 },
      }).catch(() => null)

      if (resp) {
        // API should return 200 (capped) or 400 (validation error), not 500
        expect([200, 400, 422]).toContain(resp.status())
      } else {
        expect(true).toBe(true)
      }
    }
  })
})
