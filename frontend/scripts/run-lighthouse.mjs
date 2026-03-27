import { spawn } from 'node:child_process'
import { once } from 'node:events'
import { setTimeout as delay } from 'node:timers/promises'
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import lighthouse from 'lighthouse'
import { launch as launchChrome } from 'chrome-launcher'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const frontendDir = path.resolve(__dirname, '..')
const analyticsDir = path.join(frontendDir, 'analytics')
const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm'
const shouldSpawnServer = process.env.LH_SKIP_SERVER !== '1'

const port = Number(process.env.LH_PORT || 4120)
const baseUrl = `http://localhost:${port}`
const routes = ['/crm', '/projects', '/academy']

async function waitForServer(maxAttempts = 40, sleepMs = 500) {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    try {
      const res = await fetch(`${baseUrl}/api/health`)
      if (res.ok || res.status === 404) {
        return
      }
    } catch (_) {
      // ignore until server comes up
    }
    await delay(sleepMs)
  }
  throw new Error('Next.js server did not become ready in time')
}

async function captureRoute(route) {
  const chrome = await launchChrome({
    logLevel: 'error',
    chromeFlags: [
      '--headless=new',
      '--no-sandbox',
      '--disable-gpu',
      '--disable-dev-shm-usage',
    ],
  })

  try {
    const url = `${baseUrl}${route}`
    const runnerResult = await lighthouse(url, {
      port: chrome.port,
      output: 'json',
      onlyCategories: ['performance'],
      logLevel: 'error',
      maxWaitForLoad: 90000,
    })

    const reportPayload = Array.isArray(runnerResult.report)
      ? runnerResult.report[0]
      : runnerResult.report
    const fileName = `${route.replace(/^\//, '') || 'home'}-lh.json`
    await fs.writeFile(path.join(analyticsDir, fileName), reportPayload, 'utf-8')

    return {
      route,
      performance: runnerResult.lhr.categories.performance?.score ?? null,
      ttfb: runnerResult.lhr.audits['server-response-time']?.numericValue ?? null,
      fcp: runnerResult.lhr.audits['first-contentful-paint']?.numericValue ?? null,
      lcp: runnerResult.lhr.audits['largest-contentful-paint']?.numericValue ?? null,
    }
  } finally {
    try {
      await chrome.kill()
    } catch (error) {
      console.warn('chrome cleanup warning:', error.message)
    }
  }
}

async function run() {
  let server = null
  if (shouldSpawnServer) {
    server = spawn(npmCmd, ['run', 'start', '--', '-p', String(port)], {
      cwd: frontendDir,
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: process.platform === 'win32',
    })

    server.stdout.on('data', (chunk) => process.stdout.write(`[next] ${chunk}`))
    server.stderr.on('data', (chunk) => process.stderr.write(`[next] ${chunk}`))
  }

  try {
    await waitForServer()
    const metrics = []
    for (const route of routes) {
      console.log(`Measuring ${baseUrl}${route}`)
      const result = await captureRoute(route)
      metrics.push(result)
    }

    console.table(
      metrics.map((m) => ({
        route: m.route,
        performance: m.performance,
        ttfb_ms: m.ttfb,
        fcp_ms: m.fcp,
        lcp_ms: m.lcp,
      })),
    )
  } finally {
    if (server) {
      server.kill('SIGTERM')
      await once(server, 'close')
    }
  }
}

run().catch((error) => {
  console.error('Failed to capture Lighthouse baselines:', error)
  process.exitCode = 1
})
