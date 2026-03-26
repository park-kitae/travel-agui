// 폼 제출 후 메시지 확인
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  // 콘솔 로그 캡처
  page.on('console', msg => {
    console.log(`[Browser] ${msg.type()}: ${msg.text()}`);
  });

  try {
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');

    console.log('Step 1: 메시지 전송');
    await page.fill('.input-box', '도쿄 호텔 예약하고 싶어요');
    await page.click('.send-btn');

    console.log('Step 2: 폼 대기...');
    await page.waitForSelector('.user-input-form', { timeout: 15000 });
    console.log('✅ 폼 나타남');

    console.log('\nStep 3: 폼 입력');
    await page.fill('input[id="check_in"]', '2024-06-10');
    await page.fill('input[id="check_out"]', '2024-06-14');
    await page.fill('input[id="guests"]', '2');

    console.log('Step 4: 제출 버튼 클릭');
    await page.click('.form-submit-btn');
    console.log('✅ 제출 완료');

    // 30초 동안 메시지 변화 확인
    console.log('\nStep 5: 30초 동안 상태 모니터링...\n');
    for (let i = 0; i < 15; i++) {
      await page.waitForTimeout(2000);

      const messages = await page.locator('.message-row').count();
      const formVisible = await page.locator('.user-input-form:visible').count();
      const toolCards = await page.locator('.tool-card').count();

      console.log(`[${(i + 1) * 2}초] 메시지: ${messages}개, 폼 표시: ${formVisible > 0 ? 'YES' : 'NO'}, 결과카드: ${toolCards}개`);

      if (toolCards > 0) {
        console.log('\n✅ 호텔 검색 결과 나타남!');
        break;
      }
    }

    // 모든 메시지 내용 출력
    console.log('\n=== 모든 메시지 내용 ===\n');
    const allMessages = await page.locator('.message-row').all();
    for (let i = 0; i < allMessages.length; i++) {
      const role = await allMessages[i].getAttribute('class');
      const text = await allMessages[i].locator('.bubble').allTextContents();
      console.log(`메시지 ${i + 1} (${role.includes('user') ? '사용자' : 'AI'}):`);
      text.forEach(t => console.log(`  ${t.trim()}`));
      console.log();
    }

    await page.screenshot({ path: 'test-form-submit-final.png', fullPage: true });
    console.log('스크린샷: test-form-submit-final.png');

    await page.waitForTimeout(5000);

  } catch (error) {
    console.error('\n에러:', error.message);
    await page.screenshot({ path: 'test-form-submit-error.png', fullPage: true });
  } finally {
    await browser.close();
  }
})();
