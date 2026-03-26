// 어시스턴트 응답 내용 확인
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');

    console.log('메시지 전송 중...');
    await page.fill('.input-box', '도쿄 호텔 예약하고 싶어요');
    await page.click('.send-btn');

    // 응답 완료 대기 (30초)
    await page.waitForTimeout(30000);

    // 모든 메시지 텍스트 출력
    const messages = await page.locator('.message-row').all();
    console.log(`\n총 ${messages.length}개의 메시지:\n`);

    for (let i = 0; i < messages.length; i++) {
      const role = await messages[i].getAttribute('class');
      const bubbles = await messages[i].locator('.bubble').all();

      console.log(`\n=== 메시지 ${i + 1} (${role.includes('user') ? '사용자' : '어시스턴트'}) ===`);

      for (let j = 0; j < bubbles.length; j++) {
        const text = await bubbles[j].textContent();
        console.log(text.trim());
      }

      // 툴 호출 확인
      const toolIndicators = await messages[i].locator('.tool-call-indicator').count();
      if (toolIndicators > 0) {
        console.log('\n[툴 호출 감지됨]');
        const toolNames = await messages[i].locator('.tool-name').allTextContents();
        toolNames.forEach(name => console.log(`  - ${name}`));
      }

      // 폼 확인
      const forms = await messages[i].locator('.user-input-form').count();
      if (forms > 0) {
        console.log('\n[사용자 입력 폼 감지됨]');
      }

      // 결과 카드 확인
      const toolCards = await messages[i].locator('.tool-card').count();
      if (toolCards > 0) {
        console.log(`\n[결과 카드 ${toolCards}개 감지됨]`);
      }
    }

    await page.screenshot({ path: 'test-response-check.png', fullPage: true });
    console.log('\n\n스크린샷: test-response-check.png');

    await page.waitForTimeout(5000);

  } catch (error) {
    console.error('에러:', error.message);
  } finally {
    await browser.close();
  }
})();
