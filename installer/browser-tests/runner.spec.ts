import assert from "node:assert/strict";
import { test, expect } from "../testing/browserApi";
import { assertionSignal } from "../testing/browserAssertions";

test("runner conformance: locator retries and negation preserve browser semantics", async ({
  page,
}) => {
  await page.setContent(`<button id="ready" class="ready" data-state="yes">hello\n world</button>
    <input id="check" type="checkbox" checked><button id="disabled" disabled>Disabled</button>
    <div id="hidden" hidden>Hidden</div><div id="off" style="position:absolute;top:5000px">Off screen</div>
    <span class="item">one</span><span class="item">two</span>`);
  const ready = page.locator("#ready");
  await expect(ready).toBeVisible();
  await expect(ready).not.toBeHidden();
  await expect(page.locator("#hidden")).toBeHidden();
  await expect(page.locator("#missing")).not.toBeVisible();
  await expect(ready).toHaveText("hello world");
  await expect(ready).toHaveText(/hello\s+world/);
  await expect(ready).toContainText("world");
  await expect(page.locator(".item")).toHaveText(["one", "two"]);
  await expect(page.locator(".item")).toContainText(["two"]);
  await expect(ready).toHaveAttribute("data-state", /YES/i);
  await expect(ready).toHaveAttribute("data-state");
  await expect(ready).not.toHaveAttribute("missing");
  await expect(ready).toHaveClass(/ready/);
  await expect(page.locator("#hidden")).toHaveCSS("display", "none");
  await expect(page.locator(".item")).toHaveCount(2);
  await expect(page.locator(".item")).not.toHaveCount(1);
  await expect(page.locator("#disabled")).toBeDisabled();
  await expect(ready).toBeEnabled();
  await expect(ready).not.toBeDisabled();
  await expect(page.locator("#check")).toBeChecked();
  await ready.focus();
  await expect(ready).toBeFocused();
  await expect(ready).toBeInViewport();
  await expect(page.locator("#off")).not.toBeInViewport();
  await page.evaluate(() =>
    setTimeout(() => {
      document.querySelector("#ready")!.textContent = "changed";
    }, 50),
  );
  await expect(ready).toHaveText("changed");
  const options = { timeout: 50 };
  for (const failure of [
    () => expect(ready).toHaveText("wrong", options),
    () => expect(ready).not.toHaveText("changed", options),
    () => expect(page.locator(".item")).toHaveCount(99, options),
    () => expect(ready).toHaveAttribute("data-state", "wrong", options),
    () => expect(ready).toHaveCSS("display", "none", options),
    () => expect(ready).toBeHidden(options),
  ])
    await assert.rejects(failure, assert.AssertionError);
});

test("runner conformance: polling failures and cancellation cannot pass", async ({
  page,
}) => {
  await page.setContent('<div id="present">present</div>');
  let value = 0;
  setTimeout(() => (value = 1), 30);
  await expect.poll(() => value, { timeout: 1000, intervals: [10] }).toBe(1);
  await assert.rejects(() =>
    expect
      .poll(() => 5, { timeout: 50, intervals: [10] })
      .toBeLessThanOrEqual(4),
  );
  await assert.rejects(
    () => expect(page.locator("#present")).not.toBeVisible({ timeout: 50 }),
    assert.AssertionError,
  );
  const controller = new AbortController();
  const previous = assertionSignal(controller.signal);
  try {
    controller.abort();
    await assert.rejects(
      () => expect(page.locator("#present")).toBeVisible(),
      assert.AssertionError,
    );
  } finally {
    assertionSignal(previous);
  }
});
