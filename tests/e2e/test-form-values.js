// 폼 값 확인 테스트
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');

    await page.fill('.input-box', '도쿄 호텔 예약하고 싶어요');
    await page.click('.send-btn');

    await page.waitForSelector('.user-input-form', { timeout: 15000 });
    console.log('✅ 폼 나타남\n');

    // 폼 필드 입력
    console.log('입력 전 값 확인:');
    const checkInBefore = await page.inputValue('input[id="check_in"]');
    const checkOutBefore = await page.inputValue('input[id="check_out"]');
    const guestsBefore = await page.inputValue('input[id="guests"]');
    console.log(`  check_in: "${checkInBefore}"`);
    console.log(`  check_out: "${checkOutBefore}"`);
    console.log(`  guests: "${guestsBefore}"`);

    console.log('\n값 입력 중...');
    await page.fill('input[id="check_in"]', '2024-06-10');
    await page.fill('input[id="check_out"]', '2024-06-14');
    await page.fill('input[id="guests"]', '2');

    // 입력 후 대기
    await page.waitForTimeout(1000);

    console.log('\n입력 후 값 확인:');
    const checkInAfter = await page.inputValue('input[id="check_in"]');
    const checkOutAfter = await page.inputValue('input[id="check_out"]');
    const guestsAfter = await page.inputValue('input[id="guests"]');
    console.log(`  check_in: "${checkInAfter}"`);
    console.log(`  check_out: "${checkOutAfter}"`);
    console.log(`  guests: "${guestsAfter}"`);

    // 제출 버튼 확인
    console.log('\n제출 버튼 상태:');
    const submitBtn = await page.locator('.form-submit-btn');
    const isDisabled = await submitBtn.isDisabled();
    const buttonText = await submitBtn.textContent();
    console.log(`  텍스트: "${buttonText}"`);
    console.log(`  disabled: ${isDisabled}`);

    console.log('\n제출 버튼 클릭...');
    await page.click('.form-submit-btn');
    console.log('클릭 완료!');

    await page.waitForTimeout(5000);

    await page.screenshot({ path: 'test-form-values.png', fullPage: true });

  } catch (error) {
    console.error('\n에러:', error.message);
    await page.screenshot({ path: 'test-form-values-error.png', fullPage: true });
  } finally {
    await browser.close();
  }
})();
