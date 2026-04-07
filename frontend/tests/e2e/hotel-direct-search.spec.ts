import { test, expect } from '@playwright/test';
import {
  gotoApp,
  selectors,
  sendUserMessage,
  takeScreenshot,
  waitForHotelResults,
} from './utils/testHelpers';

test('호텔 직접 검색 - 자연어로 모든 정보 제공', async ({ page }) => {
  await gotoApp(page);

  await sendUserMessage(page, '도쿄 호텔 추천해줘 (6월 10일~14일, 2명)');
  await waitForHotelResults(page, 15000);

  await expect(page.locator(selectors.toolCard)).toHaveCount(1);
  await expect(page.locator(selectors.hotelItem)).toHaveCount(3);
  await expect(page.locator(selectors.hotelName).first()).not.toBeEmpty();

  await takeScreenshot(page, 'test-hotel-direct.png');
});
