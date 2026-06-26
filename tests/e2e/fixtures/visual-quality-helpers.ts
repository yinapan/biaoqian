import { Page, TestInfo } from '@playwright/test'

export async function attachVisualFailureArtifacts(page: Page, info: TestInfo, failedImgUrl?: string) {
  const screenshot = await page.screenshot({ fullPage: true })
  await info.attach('screenshot', { body: screenshot, contentType: 'image/png' })

  const consoleLogs: string[] = []
  page.on('console', msg => consoleLogs.push(`[${msg.type()}] ${msg.text()}`))
  page.on('pageerror', err => consoleLogs.push(`[pageerror] ${err.message}`))
  await info.attach('console-logs', { body: consoleLogs.join('\n'), contentType: 'text/plain' })

  if (failedImgUrl) {
    await info.attach('failed-image-url', { body: failedImgUrl, contentType: 'text/plain' })
  }
}

export async function getNaturalSize(page: Page, selector: string) {
  return await page.locator(selector).evaluate((el: HTMLImageElement) => ({
    w: el.naturalWidth,
    h: el.naturalHeight,
  }))
}

export async function getRenderedSize(page: Page, selector: string) {
  const box = await page.locator(selector).boundingBox()
  return { w: box!.width, h: box!.height }
}

export async function getObjectFit(page: Page, selector: string) {
  return await page.locator(selector).evaluate(
    (el: HTMLImageElement) => getComputedStyle(el).objectFit
  )
}
