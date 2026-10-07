import {test,expect} from '@playwright/test';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
async function audit(page:import('@playwright/test').Page){
  await page.addScriptTag({path:require.resolve('axe-core/axe.min.js')});
  const violations=await page.evaluate(async()=>{const a=(window as unknown as {axe:{run:(options:unknown)=>Promise<{violations:unknown[]}>}}).axe;return (await a.run({runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})).violations;});
  expect(violations).toEqual([]);
}
test('desktop contrast, keyboard access, progress and completion',async({page})=>{
  await page.setViewportSize({width:1140,height:1000});await page.goto('/');
  await expect(page.getByRole('heading',{name:'Partially installed',exact:true})).toBeVisible();
  await audit(page);await page.screenshot({path:'test-results/overview-desktop.png',fullPage:true});
  await page.keyboard.press('Tab');await expect(page.getByText('Skip to main content')).toBeFocused();
  await page.getByRole('button',{name:'Install Development Environment'}).click();
  await expect(page.getByRole('progressbar')).toBeVisible();
  await expect(page.getByRole('heading',{name:'Development environment ready.'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Development environment ready.'})).toBeFocused();
  await audit(page);await page.getByRole('button',{name:'View validation results'}).click();
  await expect(page.getByRole('table')).toBeVisible();await audit(page);
  await page.screenshot({path:'test-results/validation-desktop.png',fullPage:true});
});
test('mobile layout and labels',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.goto('/');
  await expect(page.getByRole('heading',{name:'Partially installed',exact:true})).toBeVisible();
  await audit(page);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.screenshot({path:'test-results/overview-mobile.png',fullPage:true});
});
