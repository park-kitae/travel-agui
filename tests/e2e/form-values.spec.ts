import { test, expect } from '@playwright/test';
import {
  gotoApp,
  selectors,
  sendUserMessage,
  takeScreenshot,
  waitForForm,
} from './utils/testHelpers';

test('폼 값 확인 테스트 - 입력 전/후 폼 값', async ({ page }) => {
  await gotoApp(page);

  await sendUserMessage(page, '도쿄 호텔 예약하고 싶어요');
  await waitForForm(page);

  const checkInBefore = await page.inputValue(selectors.checkInInput);
  const checkOutBefore = await page.inputValue(selectors.checkOutInput);
  const guestsBefore = await page.inputValue(selectors.guestsInput);

  expect(checkInBefore).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  expect(checkOutBefore).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  expect(guestsBefore).toBe('2');
  await expect(page.locator(selectors.formSubmitButton)).toHaveText('제출');
  await expect(page.locator(selectors.formSubmitButton)).toBeEnabled();

  await page.fill(selectors.checkInInput, '2024-06-10');
  await page.fill(selectors.checkOutInput, '2024-06-14');
  await page.fill(selectors.guestsInput, '2');

  await expect(page.locator(selectors.checkInInput)).toHaveValue('2024-06-10');
  await expect(page.locator(selectors.checkOutInput)).toHaveValue('2024-06-14');
  await expect(page.locator(selectors.guestsInput)).toHaveValue('2');

  await page.click(selectors.formSubmitButton);
  await expect(page.locator(selectors.toolCard).first()).toBeVisible();

  await takeScreenshot(page, 'test-form-values.png');
});
