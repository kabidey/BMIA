#!/usr/bin/env node
/**
 * Chart smoke test — post-build, pre-deploy.
 *
 * Spins up a headless Chromium against the reachable BMIA app and asserts
 * that every chart-heavy route actually mounts recharts SVG elements.
 * Exits 0 on PASS, non-zero on FAIL so it can gate a deploy in CI.
 *
 * USAGE:
 *   node scripts/check-charts.js                        # uses REACT_APP_BACKEND_URL from .env
 *   BMIA_URL=https://bmia.smifs.com node scripts/check-charts.js
 *   BMIA_EMAIL=foo@x BMIA_PASSWORD=bar node scripts/check-charts.js
 *
 * Exit codes:
 *   0 — all routes rendered >= N recharts SVGs
 *   1 — a route rendered zero SVGs (the v3 + React 19 blank-chart bug)
 *   2 — auth / navigation failure (environment issue, not a chart bug)
 */
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

// ── Resolve URL + creds from env / .env files ───────────────────────────
function readEnv(file, key) {
  try {
    const txt = fs.readFileSync(file, 'utf8');
    const m = txt.match(new RegExp(`^${key}=(.+)$`, 'm'));
    return m ? m[1].trim() : null;
  } catch { return null; }
}

const BMIA_URL = (
  process.env.BMIA_URL
  || process.env.REACT_APP_BACKEND_URL
  || readEnv(path.join(__dirname, '..', '.env'), 'REACT_APP_BACKEND_URL')
  || 'http://localhost:3000'
).replace(/\/$/, '');

const EMAIL = process.env.BMIA_EMAIL || 'somnath.dey@smifs.com';
const PASSWORD = process.env.BMIA_PASSWORD || 'admin123';

// ── Chrome executable: system chromium or Puppeteer download ────────────
function findChromium() {
  for (const p of [
    process.env.PUPPETEER_EXECUTABLE_PATH,
    '/usr/bin/chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium-browser',
    '/root/bin/chromium',
  ]) { if (p && fs.existsSync(p)) return p; }
  throw new Error('No Chromium found; set PUPPETEER_EXECUTABLE_PATH');
}

// Each entry: { route, testid (optional pre-click), minSvgs, waitMs, name }
const CHECKS = [
  { name: 'Cockpit (Market Overview)', route: '/',           minSvgs: 2, waitMs: 10000 },
  { name: 'Big Market — Intel tab',   route: '/big-market',  minSvgs: 1, waitMs: 8000, click: 'intel-tab' },
];

// ── Main ────────────────────────────────────────────────────────────────
(async () => {
  const start = Date.now();
  console.log(`◆ BMIA chart smoke test against ${BMIA_URL}`);
  let browser;
  try {
    browser = await puppeteer.launch({
      executablePath: findChromium(),
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    });
  } catch (e) {
    console.error(`✖ Failed to launch Chromium: ${e.message}`);
    process.exit(2);
  }

  let authToken = null;
  try {
    // Login via API: navigate to the app first so fetch runs from the same
    // origin (avoids CORS / opaque-origin issues for fetch()).
    const page0 = await browser.newPage();
    await page0.goto(`${BMIA_URL}/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const resp = await page0.evaluate(async (email, pwd) => {
      try {
        const r = await fetch(`/api/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password: pwd }),
        });
        if (!r.ok) return { error: `HTTP ${r.status}` };
        return await r.json();
      } catch (e) { return { error: String(e) }; }
    }, EMAIL, PASSWORD);
    authToken = resp && resp.token;
    await page0.close();
    if (!authToken) {
      console.error(`✖ Auth failed for ${EMAIL}: ${JSON.stringify(resp).slice(0, 200)}`);
      await browser.close();
      process.exit(2);
    }
  } catch (e) {
    console.error(`✖ Auth request errored: ${e.message}`);
    await browser.close();
    process.exit(2);
  }

  const failures = [];
  for (const chk of CHECKS) {
    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1000 });
    // Pre-set auth token in localStorage before first navigation
    try {
      await page.goto(`${BMIA_URL}/`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.evaluate((tok) => localStorage.setItem('bmia_session_token', tok), authToken);
    } catch (e) {
      failures.push({ chk, reason: `initial nav failed: ${e.message}` });
      await page.close(); continue;
    }

    try {
      await page.goto(`${BMIA_URL}${chk.route}`, { waitUntil: 'domcontentloaded', timeout: 30000 });
      if (chk.click) {
        await page.waitForSelector(`[data-testid="${chk.click}"]`, { timeout: 15000 });
        await page.click(`[data-testid="${chk.click}"]`);
      }
      await new Promise(r => setTimeout(r, chk.waitMs));
      const svgCount = await page.evaluate(() => document.querySelectorAll('svg.recharts-surface').length);
      const svgNonEmpty = await page.evaluate(() =>
        Array.from(document.querySelectorAll('svg.recharts-surface'))
          .filter(s => s.children.length > 2).length
      );
      const verdict = svgNonEmpty >= chk.minSvgs ? '✓ PASS' : '✖ FAIL';
      console.log(`  ${verdict}  ${chk.name.padEnd(32)}  svgs=${svgCount} non_empty=${svgNonEmpty} (need ≥${chk.minSvgs})`);
      if (svgNonEmpty < chk.minSvgs) failures.push({ chk, svgCount, svgNonEmpty });
    } catch (e) {
      console.error(`  ✖ FAIL  ${chk.name}: ${e.message}`);
      failures.push({ chk, reason: e.message });
    } finally {
      await page.close();
    }
  }

  await browser.close();
  const ms = Date.now() - start;
  if (failures.length === 0) {
    console.log(`\n◆ PASS — all ${CHECKS.length} chart routes rendered recharts SVGs (${ms}ms)`);
    process.exit(0);
  }
  console.error(`\n◆ FAIL — ${failures.length}/${CHECKS.length} route(s) rendered blank/empty charts`);
  console.error('  → likely a recharts / react / react-is dep-tree drift');
  console.error('  → run:  yarn why react-is   and verify react-is@19.x');
  process.exit(1);
})().catch(e => {
  console.error('✖ Unhandled error:', e);
  process.exit(2);
});
