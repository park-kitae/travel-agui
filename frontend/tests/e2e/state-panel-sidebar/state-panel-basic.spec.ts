import { test, expect } from '@playwright/test';

test.describe('StatePanel SideBar E2E', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('초기 로드 시 StatePanel은 기본 숨김이고 팝업에서 기본값 확인', async ({ page }) => {
    const statePanel = page.locator('.state-panel');
    await expect(statePanel).toBeHidden();

    await page.getByRole('button', { name: '상태 보기' }).click();
    await expect(page.getByRole('dialog', { name: '상태 뷰어' })).toBeVisible();
    await expect(statePanel).toBeVisible();

    // 섹션 헤더 확인
    await expect(page.locator('text=CLIENT → SERVER')).toBeVisible();
    await expect(page.locator('text=SERVER → CLIENT')).toBeVisible();

    // 초기값 "-" 확인
    const destinationField = page.locator('.sp-field', { hasText: '도착지' });
    await expect(destinationField.locator('.sp-field-value')).toHaveText('-');
  });

  test('모바일에서도 상태 보기 버튼으로 팝업을 열고 닫을 수 있다', async ({ page }) => {
    await page.setViewportSize({ width: 800, height: 800 });
    const statePanel = page.locator('.state-panel');

    await expect(statePanel).toBeHidden();

    await page.getByRole('button', { name: '상태 보기' }).click();
    const dialog = page.getByRole('dialog', { name: '상태 뷰어' });
    await expect(dialog).toBeVisible();
    await expect(statePanel).toBeVisible();

    await page.getByRole('button', { name: '상태 뷰어 닫기' }).click();
    await expect(dialog).toBeHidden();
  });
});
