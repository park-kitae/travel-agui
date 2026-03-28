import { test, expect } from '@playwright/test';
import {
  gotoApp,
  selectors,
  sendUserMessage,
  takeScreenshot,
  waitForHotelResults,
} from './utils/testHelpers';

test('호텔 리스트 클릭 → 상세 정보 조회', async ({ page }) => {
  await gotoApp(page);

  // 1. 호텔 검색
  await sendUserMessage(page, '도쿄 호텔 추천해줘 (6월 10일~14일, 2명)');
  await waitForHotelResults(page, 20000);

  // 2. 클릭 가능한 호텔 아이템 확인
  const clickableHotel = page.locator(selectors.hotelItemClickable).first();
  await expect(clickableHotel).toBeVisible({ timeout: 10000 });

  // 호텔명과 hotel_code 텍스트 캡처 (클릭 전)
  const hotelNameText = await page.locator(selectors.hotelName).first().textContent();
  await takeScreenshot(page, 'hotel-detail-before-click.png');

  // 3. 첫 번째 호텔 클릭
  await clickableHotel.click();

  // 4. 유저 메시지 버블에 호텔 코드(HTL-) 포함 여부 확인
  const userBubbles = page.locator(selectors.userBubble);
  await expect(userBubbles.last()).toContainText('HTL-', { timeout: 5000 });

  // 5. 호텔 상세 카드가 렌더링될 때까지 대기
  await expect(page.locator(selectors.hotelDetailCard)).toBeVisible({ timeout: 20000 });

  await takeScreenshot(page, 'hotel-detail-after-click.png');

  // 6. 상세 카드 내 핵심 요소 확인
  // 설명
  await expect(page.locator(selectors.hotelDetailDescription)).not.toBeEmpty();

  // 객실 타입
  const roomItems = page.locator(selectors.hotelRoomItem);
  await expect(roomItems.first()).toBeVisible();
  expect(await roomItems.count()).toBeGreaterThan(0);

  // 어메니티 태그
  const amenityTags = page.locator(selectors.hotelAmenityTag);
  await expect(amenityTags.first()).toBeVisible();

  // 하이라이트 태그
  const highlightTags = page.locator(selectors.hotelHighlightTag);
  await expect(highlightTags.first()).toBeVisible();

  // 정책(체크인/체크아웃 등)
  await expect(page.locator(selectors.hotelDetailPolicies)).toBeVisible();

  await takeScreenshot(page, 'hotel-detail-complete.png');
});

test('호텔 상세 클릭 후 다시 호텔 리스트 재검색 가능', async ({ page }) => {
  await gotoApp(page);

  // 첫 번째 검색 및 클릭
  await sendUserMessage(page, '도쿄 호텔 추천해줘 (6월 10일~14일, 2명)');
  await waitForHotelResults(page, 20000);

  const clickableHotel = page.locator(selectors.hotelItemClickable).first();
  await expect(clickableHotel).toBeVisible({ timeout: 10000 });
  await clickableHotel.click();

  // 상세 카드 렌더링 대기
  await expect(page.locator(selectors.hotelDetailCard)).toBeVisible({ timeout: 20000 });

  // 두 번째 메시지로 다른 도시 검색
  await sendUserMessage(page, '오사카 호텔도 알려줘 (6월 10일~14일, 2명)');
  await waitForHotelResults(page, 20000);

  // 두 번째 호텔 리스트도 정상 렌더링 확인
  const allHotelItems = page.locator(selectors.hotelItem);
  expect(await allHotelItems.count()).toBeGreaterThanOrEqual(3);

  await takeScreenshot(page, 'hotel-detail-then-new-search.png');
});
