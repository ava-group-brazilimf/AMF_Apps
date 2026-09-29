// gate_mermaid_probe.js — Playwright headless probe for the Mermaid gate
//
// Usage:
//   node gate_mermaid_probe.js <htmlPath> <outputPath> <executablePath> [timeoutMs]
//
// Loads the full Summary HTML in Chromium headless, waits for Mermaid rendering
// to complete (up to timeoutMs ms), then collects per-element render status.
//
// Output JSON written to <outputPath> AND emitted to stdout as the last line.
// Exit 0 on success, 1 on fatal error (browser launch failure, etc.).
//
// Output schema:
// {
//   "diagrams": [
//     {
//       "diagram_id": "diag-c4ctx",
//       "section": null,
//       "data_src": null,
//       "rendered": true,
//       "status": "PASS"           // "PASS" | "FAIL" | "EMPTY" | "TIMEOUT"
//     }, ...
//   ],
//   "console_errors": [...],
//   "page_errors": [...]
// }

'use strict';

const fs   = require('fs');
const path = require('path');

const [,, htmlPath, outputPath, executablePath, timeoutMsStr] = process.argv;
const timeoutMs = parseInt(timeoutMsStr || '15000', 10);

if (!htmlPath || !outputPath) {
  process.stderr.write('Usage: node gate_mermaid_probe.js <htmlPath> <outputPath> <executablePath> [timeoutMs]\n');
  process.exit(1);
}

(async () => {
  // Resolve playwright from the same node_modules tree as probe_browser.js
  let chromium;
  try {
    chromium = require('playwright').chromium;
  } catch (e) {
    // Try relative path (repo root node_modules)
    const repoRoot = path.resolve(__dirname, '..', '..', '..', '..', '..', '..');
    try {
      chromium = require(path.join(repoRoot, 'node_modules', 'playwright')).chromium;
    } catch (e2) {
      const errResult = {
        probe_error: `playwright module not found: ${e.message}`,
        diagrams: [],
        console_errors: [],
        page_errors: [],
      };
      const out = JSON.stringify(errResult);
      fs.writeFileSync(outputPath, JSON.stringify(errResult, null, 2), 'utf8');
      process.stdout.write(out + '\n');
      process.exit(1);
    }
  }

  const consoleErrors = [];
  const pageErrors    = [];
  let browser;

  try {
    const launchOpts = {
      headless: true,
      args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
    };
    if (executablePath && executablePath !== 'undefined') {
      launchOpts.executablePath = executablePath;
    }

    browser = await chromium.launch(launchOpts);
    const context = await browser.newContext();
    const page    = await context.newPage();

    // Capture console errors / warnings
    page.on('console', msg => {
      const t = msg.type();
      if (t === 'error' || t === 'warning') {
        consoleErrors.push({
          type: t,
          text: msg.text(),
          location: msg.location(),
        });
      }
    });

    // Capture uncaught JS exceptions
    page.on('pageerror', err => {
      pageErrors.push({
        message: err.message || String(err),
        stack:   err.stack   || '',
      });
    });

    const fileUrl = 'file:///' + htmlPath.replace(/\\/g, '/');
    await page.goto(fileUrl, { waitUntil: 'domcontentloaded', timeout: timeoutMs });

    // Poll until all pre.mermaid elements are either rendered (have <svg>)
    // or failed (class "code-view" / "no-diagram"), or until timeoutMs elapses.
    const pollDeadline = Date.now() + timeoutMs;
    let allSettled = false;

    while (Date.now() < pollDeadline && !allSettled) {
      allSettled = await page.evaluate(() => {
        const pending = [...document.querySelectorAll('pre.mermaid')].filter(el => {
          const hasSvg     = el.querySelector('svg') !== null;
          const isCodeView = el.classList.contains('code-view');
          const isEmpty    = !el.textContent || !el.textContent.trim();
          return !hasSvg && !isCodeView && !isEmpty;
        });
        return pending.length === 0;
      });
      if (!allSettled) {
        await page.waitForTimeout(100);
      }
    }

    // Collect per-element results for all diagram-like elements
    const diagrams = await page.evaluate(() => {
      const results = [];

      // Query all mermaid, code-view and no-diagram elements
      const selectors = [
        'pre.mermaid',
        'pre.code-view',
        'pre.no-diagram',
        'pre[data-mermaid-pending]',
      ];

      const seen = new Set();
      selectors.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
          const id = el.id || null;
          if (id && seen.has(id)) return;   // de-duplicate by id
          if (id) seen.add(id);

          const hasSvg     = el.querySelector('svg') !== null;
          const isCodeView = el.classList.contains('code-view');
          const isNoDiag   = el.classList.contains('no-diagram');
          const isPending  = el.hasAttribute('data-mermaid-pending');
          const textLen    = (el.textContent || '').trim().length;
          const dataSrc    = el.getAttribute('data-src') || null;
          const section    = el.getAttribute('data-section') || null;

          let status;
          if (isNoDiag || textLen === 0) {
            status = 'EMPTY';
          } else if (hasSvg) {
            status = 'PASS';
          } else if (isCodeView) {
            status = 'FAIL';
          } else if (isPending) {
            status = 'EMPTY';   // content was never populated from D.staticDiagrams
          } else {
            status = 'TIMEOUT'; // still has mermaid class but no svg after timeout
          }

          results.push({
            diagram_id: id,
            section:    section,
            data_src:   dataSrc,
            rendered:   hasSvg,
            status:     status,
          });
        });
      });

      return results;
    });

    await browser.close();
    browser = null;

    const payload = {
      diagrams:       diagrams,
      console_errors: consoleErrors,
      page_errors:    pageErrors,
    };

    const out = JSON.stringify(payload, null, 2);
    fs.writeFileSync(outputPath, out, 'utf8');
    process.stdout.write(JSON.stringify(payload) + '\n');
    process.exit(0);

  } catch (err) {
    if (browser) {
      await browser.close().catch(() => {});
    }
    const errResult = {
      probe_error:    err.message || String(err),
      diagrams:       [],
      console_errors: consoleErrors,
      page_errors:    pageErrors,
    };
    const out = JSON.stringify(errResult, null, 2);
    try { fs.writeFileSync(outputPath, out, 'utf8'); } catch (_) {}
    process.stdout.write(JSON.stringify(errResult) + '\n');
    process.exit(1);
  }
})();
