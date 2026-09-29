const fs = require("fs");
const { chromium } = require("playwright");

(async () => {
  const [htmlPath, outputPath, executablePath] = process.argv.slice(2);
  const result = {
    probeExecuted: false,
    bundleLoaded: false,
    mermaidObjectAvailable: false,
    rendererVersion: "",
    initialized: false,
    renderStatus: "NOT_RUN",
    runtimeError: null,
    error: null,
    stack: "",
    probeEntryPoint: htmlPath,
    executionEnvironment: "playwright-chromium",
  };
  let browser;
  try {
    browser = await chromium.launch({ headless: true, executablePath });
    const page = await browser.newPage();
    page.on("pageerror", (error) => {
      result.runtimeError = String(error.message || error);
      result.stack = error.stack || "";
    });
    await page.goto("file:///" + htmlPath.replace(/\\/g, "/"), {
      waitUntil: "load",
    });
    await page.waitForTimeout(1200);
    const probe = await page.evaluate(() => {
      const value = document.body.getAttribute("data-probe");
      return value ? JSON.parse(value) : null;
    });
    if (probe) Object.assign(result, probe);
    result.probeExecuted = true;
    result.bundleLoaded = Boolean(result.bundleLoaded);
    result.mermaidObjectAvailable = Boolean(result.mermaidObjectAvailable);
    if (result.runtimeError && !result.error)
      result.error = result.runtimeError;
  } catch (error) {
    result.error = String(error.message || error);
    result.stack = error.stack || "";
  } finally {
    if (browser) await browser.close();
  }
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), "utf8");
  process.stdout.write(JSON.stringify(result));
  process.exit(
    result.rendererVersion && result.renderStatus === "PASS" ? 0 : 1,
  );
})();
