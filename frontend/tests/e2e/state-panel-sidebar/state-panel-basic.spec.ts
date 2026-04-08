import { test, expect } from '@playwright/test';

test.describe('StatePanel SideBar E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('초기 로드 시 StatePanel이 표시되고 기본값 확인', async ({ page }) => {
    const statePanel = page.locator('.state-panel');
    await expect(statePanel).toBeVisible();
    
    // 섹션 헤더 확인
    await expect(page.locator('text=CLIENT → SERVER')).toBeVisible();
    await expect(page.locator('text=SERVER → CLIENT')).toBeVisible();
    
    // 초기값 "-" 확인
    const destinationField = page.locator('.sp-field', { hasText: 'destination' });
    await expect(destinationField.locator('.sp-field-value')).toHaveText('-');
  });

  test('반응형 동작 - 모바일에서 숨김 및 토글', async ({ page }) => {
    await page.setViewportSize({ width: 800, height: 800 });
    const statePanel = page.locator('.state-panel');
    
    // 1024px 미만에서는 sp-closed 클래스 확인 (CSS 설계에 따라 다름)
    await expect(statePanel).toHaveClass(/sp-closed/);
    
    // 토글 버튼 클릭
    await page.click('.sp-toggle-btn');
    await expect(statePanel).toHaveClass(/sp-open/);
  });
});
