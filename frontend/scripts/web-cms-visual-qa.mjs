import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { chromium, devices } from '@playwright/test'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const frontendDir = path.resolve(__dirname, '..')
const outputDir = path.join(frontendDir, 'analytics', 'visual-qa')

const baseUrl = process.env.VISUAL_BASE_URL || 'http://127.0.0.1:3000'
const routes = [
  '/cms',
  '/cms/pages',
  '/cms/media',
  '/faro',
  '/faro/eventos',
  '/faro/testimonios',
  '/community/announcements',
]

const viewports = [
  { name: 'desktop', viewport: { width: 1440, height: 900 } },
  { name: 'mobile', device: devices['iPhone 13'] },
]

function fileSafe(route) {
  return route.replace(/^\//, '').replace(/\//g, '_') || 'home'
}

async function run() {
  await fs.mkdir(outputDir, { recursive: true })
  const browser = await chromium.launch({ headless: true })
  const report = []

  try {
    for (const vp of viewports) {
      const context = vp.device
        ? await browser.newContext({ ...vp.device })
        : await browser.newContext({ viewport: vp.viewport })

      const page = await context.newPage()
      const consoleErrors = []
      const pageErrors = []
      const httpErrors = []
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text())
        }
      })
      page.on('pageerror', (err) => {
        pageErrors.push(String(err))
      })
      page.on('response', (resp) => {
        const status = resp.status()
        if (status >= 400) {
          httpErrors.push({ status, url: resp.url() })
        }
      })

      for (const route of routes) {
        const url = `${baseUrl}${route}`
        const start = Date.now()
        const response = await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 })
        const durationMs = Date.now() - start
        const status = response?.status() ?? 0
        const ok = status >= 200 && status < 400

        const screenshotPath = path.join(outputDir, `${fileSafe(route)}-${vp.name}.png`)
        await page.screenshot({ path: screenshotPath, fullPage: true })

        report.push({
          viewport: vp.name,
          route,
          status,
          durationMs,
          ok,
        })
      }

      const errPath = path.join(outputDir, `errors-${vp.name}.json`)
      await fs.writeFile(
        errPath,
        JSON.stringify({ consoleErrors, pageErrors, httpErrors }, null, 2),
        'utf-8',
      )

      await context.close()
    }

    const summaryPath = path.join(outputDir, 'summary.json')
    await fs.writeFile(summaryPath, JSON.stringify(report, null, 2), 'utf-8')

    const failures = report.filter((item) => !item.ok)
    if (failures.length > 0) {
      console.table(report)
      throw new Error(`Visual QA failed on ${failures.length} route checks`)
    }

    console.table(report)
    console.log(`VISUAL_QA_OK artifacts at ${outputDir}`)
  } finally {
    await browser.close()
  }
}

run().catch((error) => {
  console.error('VISUAL_QA_FAIL', error)
  process.exitCode = 1
})
