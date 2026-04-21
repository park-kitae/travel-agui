import { test, expect } from '@playwright/test';
import { gotoApp, selectors } from '../utils/testHelpers';

function toSseBody(events: Array<Record<string, unknown>>): string {
  return events.map(event => `data: ${JSON.stringify(event)}\n\n`).join('');
}

test.describe('StatePanel Update Flow', () => {
  test.beforeEach(async ({ page }) => {
    await gotoApp(page);
  });

  test('호텔 클릭 시 UI Context 업데이트 및 하이라이트 확인', async ({ page }) => {
    // 1. 호텔 검색 시뮬레이션 (검색어 입력)
    await page.fill(selectors.inputBox, '제주도 호텔 알려줘');
    await page.click(selectors.sendButton);

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
    await page.fill(selectors.inputBox, '도쿄 2명 6월 10일 호텔');
    await page.click(selectors.sendButton);

    // StatePanel의 destination 필드가 '도쿄'로 변하는지 대기
    const destField = page.locator('.sp-field', { hasText: 'destination' });
    await expect(destField.locator('.sp-field-value')).toHaveText('도쿄', { timeout: 10000 });
    
    // 서버 하이라이트 클래스 확인
    await expect(destField).toHaveClass(/sp-highlight-server/);
    
    // 방향 화살표 펄스 확인
    const serverArrow = page.locator('.sp-arrow', { hasText: '↓' });
    await expect(serverArrow).toHaveClass(/sp-arrow-pulse/);
  });

  test('STATE_DELTA 수신 시 StatePanel이 증분 업데이트를 반영한다', async ({ page }) => {
    await page.route('**/agui/run', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: toSseBody([
          { type: 'RUN_STARTED', runId: 'run-delta', threadId: 'thread-delta' },
          {
            type: 'STATE_DELTA',
            delta: [
              { op: 'replace', path: '/travel_context/destination', value: '오사카' },
              { op: 'replace', path: '/travel_context/guests', value: 2 },
              { op: 'replace', path: '/agent_status/current_intent', value: 'searching' },
              { op: 'replace', path: '/agent_status/active_tool', value: 'search_hotels' },
              { op: 'replace', path: '/user_preferences/hotel_grade', value: '4성' },
            ],
          },
          { type: 'RUN_FINISHED', runId: 'run-delta', threadId: 'thread-delta' },
        ]),
      });
    });

    await page.fill(selectors.inputBox, '오사카 호텔 찾아줘');
    await page.click(selectors.sendButton);

    const destinationField = page.locator('.sp-field', { hasText: '도착지' });
    await expect(destinationField.locator('.sp-field-value')).toHaveText('오사카');

    const guestsField = page.locator('.sp-field', { hasText: '인원 (명)' });
    await expect(guestsField.locator('.sp-field-value')).toHaveText('2');

    const intentField = page.locator('.sp-field', { hasText: '인텐트' });
    await expect(intentField.locator('.sp-field-value')).toHaveText('searching');

    const hotelGradeField = page.locator('.sp-field', { hasText: '호텔 등급' });
    await expect(hotelGradeField.locator('.sp-field-value')).toHaveText('4성');
  });
});
