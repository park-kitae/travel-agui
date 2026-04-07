import { test, expect } from '@playwright/test';
import {
  clearConversation,
  gotoApp,
  selectors,
  sendUserMessage,
  takeScreenshot,
  waitForForm,
} from './utils/testHelpers';

test('기본값 테스트 - 도시 언급 시/않을 때', async ({ page }) => {
  await gotoApp(page);

  await sendUserMessage(page, '호텔 예약하고 싶어요');
  await waitForForm(page);

  const checkInValue = await page.inputValue(selectors.checkInInput);
  const checkOutValue = await page.inputValue(selectors.checkOutInput);
  const guestsValue = await page.inputValue(selectors.guestsInput);
  const daysDiff = (new Date(checkOutValue).getTime() - new Date(checkInValue).getTime()) / (1000 * 60 * 60 * 24);

  await expect(page.locator(selectors.cityInput)).toHaveValue('');
  expect(checkInValue).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  expect(checkOutValue).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  expect(guestsValue).toBe('2');
  expect(daysDiff).toBe(1);

  await takeScreenshot(page, 'test-default-values-no-city.png');

  await clearConversation(page);

  await sendUserMessage(page, '도쿄 호텔 예약하고 싶어요');
  await waitForForm(page);

  await expect(page.locator(selectors.cityInput)).toHaveValue('도쿄');
  await expect(page.locator(selectors.checkInInput)).not.toHaveValue('');
  await expect(page.locator(selectors.checkOutInput)).not.toHaveValue('');
  await expect(page.locator(selectors.guestsInput)).toHaveValue('2');

  await takeScreenshot(page, 'test-default-values-with-city.png');
});
