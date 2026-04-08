import { test, expect } from '@playwright/test';

test.describe('StatePanel Update Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('호텔 클릭 시 UI Context 업데이트 및 하이라이트 확인', async ({ page }) => {
    // 1. 호텔 검색 시뮬레이션 (검색어 입력)
    await page.fill('textarea[placeholder*="메시지를 입력하세요"]', '제주도 호텔 알려줘');
    await page.click('button:has-text("전송")');

    // 2. 호텔 카드가 나타날 때까지 대기
    const hotelCard = page.locator('.tool-card').first();
    await hotelCard.waitFor({ state: 'visible', timeout: 10000 });

    // 3. 호텔 클릭
    await hotelCard.click();

    // 4. StatePanel의 selected_hotel 필드 확인
    const hotelField = page.locator('.sp-field', { hasText: 'selected_hotel' });
    const value = hotelField.locator('.sp-field-value');
    await expect(value).not.toHaveText('-');
    
    // 5. 하이라이트 클래스 확인
    await expect(hotelField).toHaveClass(/sp-highlight-client/);
    
    // 6. current_view 업데이트 확인
    const viewField = page.locator('.sp-field', { hasText: 'current_view' });
    await expect(viewField.locator('.sp-field-value')).toHaveText('hotel_detail');
  });

  test('서버 응답 시 Travel Context 업데이트 및 하이라이트 확인', async ({ page }) => {
    await page.fill('textarea[placeholder*="메시지를 입력하세요"]', '도쿄 2명 6월 10일 호텔');
    await page.click('button:has-text("전송")');

    // StatePanel의 destination 필드가 '도쿄'로 변하는지 대기
    const destField = page.locator('.sp-field', { hasText: 'destination' });
    await expect(destField.locator('.sp-field-value')).toHaveText('도쿄', { timeout: 10000 });
    
    // 서버 하이라이트 클래스 확인
    await expect(destField).toHaveClass(/sp-highlight-server/);
    
    // 방향 화살표 펄스 확인
    const serverArrow = page.locator('.sp-arrow', { hasText: '↓' });
    await expect(serverArrow).toHaveClass(/sp-arrow-pulse/);
  });
});
