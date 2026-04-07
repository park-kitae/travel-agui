import { test, expect } from '@playwright/test';
import {
  gotoApp,
  selectors,
  sendUserMessage,
  takeScreenshot,
  waitForForm,
  waitForHotelResults,
} from './utils/testHelpers';

test('폼 제출 테스트 - 호텔 검색 결과', async ({ page }) => {
  await gotoApp(page);

  await sendUserMessage(page, '도쿄 호텔 예약하고 싶어요');
  await waitForForm(page);

  await page.fill(selectors.checkInInput, '2024-06-10');
  await page.fill(selectors.checkOutInput, '2024-06-14');
  await page.fill(selectors.guestsInput, '2');
  await page.click(selectors.formSubmitButton);

  await waitForHotelResults(page, 30000);

  await expect(page.locator(selectors.toolCard)).toHaveCount(1);
  await expect(page.locator(selectors.hotelItem)).toHaveCount(3);
  await expect(page.locator(selectors.messageRows)).toHaveCount(4);

  await takeScreenshot(page, 'test-form-submit-final.png');
});
