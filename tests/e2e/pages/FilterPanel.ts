import { Page, Locator } from '@playwright/test'

// Inline slug logic mirroring frontend/src/utils/testid.ts
// Kept local to avoid cross-package import issues in the standalone e2e package
function slug(v: string): string {
  return v
    .trim()
    .toLowerCase()
    .replace(/[^\w一-鿿]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

export class FilterPanel {
  constructor(private page: Page) {}

  group(field: string): Locator {
    return this.page.locator(`[data-testid="filter-group-${field}"]`)
  }

  option(field: string, value: string): Locator {
    return this.page.locator(`[data-testid="filter-option-${field}-${slug(value)}"]`)
  }

  range(field: string): Locator {
    return this.page.locator(`[data-testid="filter-range-${field}"]`)
  }

  async clearAll() {
    // Click clear-all button if present, else reset each filter
    const clearBtn = this.page.locator('[data-testid="filter-clear-all"]')
    const count = await clearBtn.count()
    if (count > 0) {
      const reqPromise = this.page.waitForRequest(r =>
        r.url().includes('/api/v1/search/query')
      ).catch(() => null)
      await clearBtn.click()
      await reqPromise
      await this.page.waitForLoadState('networkidle').catch(() => {})
    }
  }
}
