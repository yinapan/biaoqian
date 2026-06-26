import { Page, Locator, expect } from '@playwright/test'

export class AssetDetailModal {
  constructor(private page: Page) {}

  get modal(): Locator {
    return this.page.locator('[data-testid="detail-modal"]')
  }

  get previewImage(): Locator {
    return this.page.locator('[data-testid="detail-preview"]')
  }

  preview(): Locator {
    return this.page.locator('[data-testid="detail-preview"]')
  }

  copyPath(): Locator {
    return this.page.locator('[data-testid="copy-path-btn"]')
  }

  copyId(): Locator {
    return this.page.locator('[data-testid="copy-id-btn"]')
  }

  async expectOpen() {
    await expect(this.modal).toBeVisible()
  }

  async expectClose() {
    await expect(this.modal).not.toBeVisible()
  }

  async close() {
    // detail-close is el-dialog internal; use ESC to close
    await this.page.keyboard.press('Escape')
    await expect(this.modal).not.toBeVisible()
  }

  async closeViaOverlay() {
    // Click the overlay backdrop (el-overlay) outside the dialog
    await this.page.locator('.el-overlay').click({ position: { x: 10, y: 10 } })
    await this.page.waitForTimeout(300)
  }

  async closeViaButton() {
    // el-dialog close button
    await this.page.locator('.el-dialog__headerbtn').click()
    await this.page.waitForTimeout(300)
  }
}
