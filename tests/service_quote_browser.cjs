const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const {chromium} = require("playwright");

(async () => {
  const browser = await chromium.launch({headless:true,
    ...(process.env.CHROMIUM_PATH ? {executablePath:process.env.CHROMIUM_PATH} : {})});
  const base = process.env.SERVICE_QUOTE_BASE_URL || "http://127.0.0.1:5055";
  try {
    for (const width of [1440, 390, 360, 320]) {
      const context = await browser.newContext({viewport:{width,height:900},
        isMobile:width<600,hasTouch:width<600,acceptDownloads:true});
      const page = await context.newPage();
      const errors = [];
      page.on("pageerror", error => errors.push(error.message));
      await page.goto(base + "/tools/");
      await page.getByRole("link", {name:"Price a job"}).click();
      assert.equal(await page.locator("#sq-inputs").isDisabled(), false);
      assert.equal(await page.locator("#sq-result").isHidden(), true);
      await page.locator("#sq-example").click();
      await page.locator("#sq-calculate").click();
      assert.equal(await page.locator("#sq-cost-result").textContent(), "$420.00");
      assert.equal(await page.locator("#sq-quote-result").textContent(), "$646.16");
      assert.equal(await page.locator("#sq-profit-result").textContent(), "$226.16");
      assert.equal(await page.locator("#sq-margin-result").textContent(), "35.0%");
      const downloading = page.waitForEvent("download");
      await page.locator("#sq-download").click();
      const download = await downloading;
      const report = await fs.readFile(await download.path(), "utf8");
      assert.match(report, /Suggested quote before tax: \$646.16/);
      assert.match(report, /Allocated overhead: \$55.00/);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await page.locator("#materials").fill("200");
      assert.equal(await page.locator("#sq-result").isHidden(), true);
      await page.locator("#sq-calculate").click();
      assert.equal(await page.locator("#sq-cost-result").textContent(), "$455.00");
      await page.locator("#margin").fill("90.1");
      await page.locator("#sq-calculate").click();
      assert.equal(await page.locator("#margin").evaluate(el => el.validity.rangeOverflow), true);
      assert.equal(await page.locator("#sq-result").isHidden(), true);
      await page.locator("#margin").fill("35");
      await page.getByRole("button", {name:"Clear",exact:true}).click();
      assert.equal(await page.locator("#materials").inputValue(), "0.00");
      assert.equal(await page.locator("#sq-result").isHidden(), true);
      await page.getByRole("link", {name:"create an invoice"}).click();
      assert.ok(page.url().endsWith("/tools/free-invoice-maker"));
      await page.goBack();
      await page.getByRole("link", {name:"← All tools"}).click();
      assert.ok(page.url().endsWith("/tools/"));
      assert.equal(await page.evaluate(() => localStorage.length), 0);
      assert.deepEqual(errors, []);
      await page.screenshot({path:"/tmp/service-quote-" + width + ".png",fullPage:true});
      await context.close();
      console.log(width + "px: quote, validation, download, privacy, navigation and overflow passed");
    }
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error);process.exitCode = 1;});
