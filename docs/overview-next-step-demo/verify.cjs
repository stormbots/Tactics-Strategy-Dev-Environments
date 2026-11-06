// Prototype-only checks. Uses the repository's existing test dependencies.
const { chromium } = require('../../installer/node_modules/@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.DEMO_CHROMIUM || '/usr/bin/chromium', args: ['--no-sandbox'] });
  const context = await browser.newContext({ reducedMotion: 'reduce' });
  const page = await context.newPage();
  const errors = [], external = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => { if (!request.url().startsWith('file:')) external.push(request.url()); });
  // Render supplied HTML directly: managed browser policy may disallow file: URLs.
  await page.setContent(fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8'));
  const scenarios = ['setup', 'unchecked', 'ready', 'repair', 'updates', 'check-failed', 'unknown', 'active', 'untrusted', 'incident'];
  const axe = fs.readFileSync(require.resolve('../../installer/node_modules/axe-core/axe.min.js'), 'utf8');
  await page.addScriptTag({ content: axe });
  for (const theme of ['dark', 'light']) {
    if (await page.locator('html').getAttribute('data-theme') !== theme) await page.getByRole('button', { name: 'Use light theme' }).click();
    for (const width of [1280, 640, 390]) {
      await page.setViewportSize({ width, height: 950 });
      for (const scenario of scenarios) {
        await page.selectOption('#scenario', scenario);
        assert.equal(await page.locator('body').getAttribute('data-state'), scenario);
        assert.equal(await page.locator('main .primary').count(), 1, `${theme}/${width}/${scenario}: one primary`);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${scenario}: horizontal overflow`);
        const issues = await page.evaluate(async () => (await axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] } })).violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) })));
        assert.deepEqual(issues, [], `${theme}/${width}/${scenario}: accessibility`);
      }
    }
  }
  await page.clock.install();
  await page.setViewportSize({ width: 1280, height: 1000 });
  await page.selectOption('#scenario', 'unchecked');
  await page.getByRole('button', { name: 'Check my setup', exact: true }).first().click();
  assert.equal(await page.locator('body').getAttribute('data-state'), 'checking');
  await page.clock.runFor(1500);
  assert.equal(await page.locator('body').getAttribute('data-state'), 'setup');
  await page.getByRole('button', { name: 'Review setup', exact: true }).click();
  await page.getByRole('button', { name: 'Install development tools', exact: true }).click();
  await page.getByRole('button', { name: 'Cancel', exact: true }).click();
  assert.equal(await page.locator('body').getAttribute('data-state'), 'review-install');
  await page.getByRole('button', { name: 'Install development tools', exact: true }).click();
  await page.getByRole('button', { name: 'Approve demo', exact: true }).click();
  assert.equal(await page.locator('body').getAttribute('data-state'), 'working');
  await page.clock.runFor(2200);
  assert.equal(await page.locator('body').getAttribute('data-state'), 'verifying');
  await page.clock.runFor(2200);
  assert.equal(await page.locator('body').getAttribute('data-state'), 'ready');
  for (const [scenario, review, execute] of [['repair', 'Review fixes', 'Repair setup'], ['updates', 'Review updates', 'Update tools']]) {
    await page.selectOption('#scenario', scenario);
    await page.getByRole('button', { name: review, exact: true }).first().click();
    await page.getByRole('button', { name: execute, exact: true }).click();
    await page.getByRole('button', { name: 'Approve demo' }).click();
    await page.clock.runFor(4400);
    assert.equal(await page.locator('body').getAttribute('data-state'), 'ready');
  }
  await page.selectOption('#scenario', 'incident');
  await page.getByRole('button', { name: 'Review interruption' }).click();
  await page.getByRole('button', { name: 'Acknowledge interruption' }).click();
  assert.equal(await page.locator('body').getAttribute('data-state'), 'unknown');
  assert(await page.getByText('Acknowledgment recorded and summary saved automatically', { exact: false }).isVisible());
  await page.getByRole('button', { name: 'Check again', exact: true }).click();
  assert.equal(await page.locator('body').getAttribute('data-state'), 'unknown');
  await page.locator('#other summary').click();
  assert(await page.getByRole('button', { name: 'Install development tools', exact: true }).isDisabled());
  await page.selectOption('#scenario', 'ready');
  await page.locator('#details summary').click();
  await page.getByRole('button', { name: 'Create support report', exact: true }).click();
  assert(await page.getByRole('dialog').getByText('This prototype collects nothing', { exact: false }).isVisible());
  await page.keyboard.press('Escape');
  assert.equal(await page.getByRole('dialog').count(), 0);
  await page.getByRole('button', { name: 'Open VSCodium', exact: true }).click();
  assert(await page.getByRole('dialog').isVisible());
  await page.getByRole('button', { name: 'Close', exact: true }).click();
  assert.deepEqual(external, [], 'No network requests');
  assert.deepEqual(errors, [], 'No browser errors');
  const output = '/tmp/sde-overview-demo'; fs.mkdirSync(output, { recursive: true });
  for (const [scenario, name] of [['setup', 'setup'], ['ready', 'ready'], ['unknown', 'paused']]) {
    await page.selectOption('#scenario', scenario);
    if (await page.locator('html').getAttribute('data-theme') !== 'dark') await page.locator('#theme').click();
    await page.locator('#other').evaluate(el => el.open = false);
    await page.locator('#details').evaluate(el => el.open = false);
    await page.screenshot({ path: path.join(output, `${name}.png`), fullPage: true });
  }
  await browser.close();
  console.log('PASS: 60 theme/viewport/scenario accessibility + reflow cases; setup/approval cancellation/repair/update/acknowledgment/support flows; no network requests or browser errors.');
  console.log(`Screenshots: ${output}`);
})().catch(error => { console.error(error); process.exit(1); });
