import { readFile } from 'node:fs/promises';
import path from 'node:path';

const cwd = process.cwd();

const pages = ['crm', 'projects', 'academy'];
const limits = {
  lcp: 4000,
  ttfb: 800,
};

function getAuditValue(report, key) {
  const value = report?.audits?.[key]?.numericValue;
  return typeof value === 'number' ? value : null;
}

async function loadJson(filePath) {
  const raw = await readFile(filePath, 'utf8');
  return JSON.parse(raw);
}

async function checkLighthouseBaselines() {
  const errors = [];
  const results = [];

  for (const page of pages) {
    const reportPath = path.join(cwd, 'analytics', `${page}-lh.json`);
    let report;
    try {
      report = await loadJson(reportPath);
    } catch (error) {
      errors.push(`Missing or invalid Lighthouse report: ${reportPath}`);
      continue;
    }

    const runtimeError = report?.runtimeError?.code;
    if (runtimeError) {
      errors.push(`Lighthouse runtime error on /${page}: ${runtimeError}`);
      continue;
    }

    const lcp = getAuditValue(report, 'largest-contentful-paint');
    const ttfb = getAuditValue(report, 'server-response-time');

    if (lcp == null) {
      errors.push(`LCP missing for /${page}`);
    } else if (lcp > limits.lcp) {
      errors.push(`LCP regression on /${page}: ${Math.round(lcp)}ms > ${limits.lcp}ms`);
    }

    if (ttfb == null) {
      errors.push(`TTFB missing for /${page}`);
    } else if (ttfb > limits.ttfb) {
      errors.push(`TTFB regression on /${page}: ${Math.round(ttfb)}ms > ${limits.ttfb}ms`);
    }

    results.push({ page, lcp, ttfb });
  }

  return { errors, results };
}

async function checkComplianceSurface() {
  const backendPath = path.join(cwd, '..', 'backend', 'api', 'workspace.py');
  const errors = [];

  let content = '';
  try {
    content = await readFile(backendPath, 'utf8');
  } catch {
    return { errors: [`Missing backend compliance file: ${backendPath}`] };
  }

  const requiredSnippets = [
    '/flags/compliance/snapshot',
    '/flags/compliance/history',
    '/flags/compliance/compare',
    '/flags/compliance/drift',
    '/flags/compliance/policy',
    '/flags/compliance/suppressions',
  ];

  for (const snippet of requiredSnippets) {
    if (!content.includes(snippet)) {
      errors.push(`Compliance endpoint missing in backend: ${snippet}`);
    }
  }

  return { errors };
}

async function main() {
  const lighthouse = await checkLighthouseBaselines();
  const compliance = await checkComplianceSurface();

  const allErrors = [...lighthouse.errors, ...compliance.errors];

  if (lighthouse.results.length) {
    console.log('[quality-gate] Lighthouse baseline metrics:');
    for (const row of lighthouse.results) {
      console.log(`- /${row.page}: LCP=${row.lcp == null ? 'n/a' : Math.round(row.lcp) + 'ms'} TTFB=${row.ttfb == null ? 'n/a' : Math.round(row.ttfb) + 'ms'}`);
    }
  }

  if (allErrors.length) {
    console.error('[quality-gate] FAILED');
    for (const item of allErrors) {
      console.error(`- ${item}`);
    }
    process.exit(1);
  }

  console.log('[quality-gate] PASSED');
}

await main();
