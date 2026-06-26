import { Page, TestInfo } from '@playwright/test'

export interface ConsoleCollector {
  logs: string[]
  attach: (info: TestInfo) => Promise<void>
}

export function startConsoleCollector(page: Page): ConsoleCollector {
  const logs: string[] = []
  page.on('console', msg => logs.push(`[${msg.type()}] ${msg.text()}`))
  page.on('pageerror', err => logs.push(`[pageerror] ${err.message}`))
  return {
    logs,
    attach: async (info: TestInfo) => {
      await info.attach('console-logs', {
        body: logs.join('\n'),
        contentType: 'text/plain',
      })
    },
  }
}

export async function attachVisualFailureArtifacts(
  page: Page,
  info: TestInfo,
  collector?: ConsoleCollector,
  failedImgUrl?: string,
) {
  const screenshot = await page.screenshot({ fullPage: true })
  await info.attach('screenshot', { body: screenshot, contentType: 'image/png' })

  if (collector) {
    await collector.attach(info)
  }

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
    (el: HTMLImageElement) => getComputedStyle(el).objectFit,
  )
}
