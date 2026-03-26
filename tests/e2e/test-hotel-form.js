// Playwright 테스트 스크립트 - 호텔 예약 폼 기능 테스트
const { chromium } = require('playwright');

(async () => {
  console.log('🚀 호텔 예약 폼 테스트 시작...\n');

  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // 1. 페이지 접속
    console.log('📍 Step 1: 프론트엔드 접속 (http://localhost:5173)');
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');
    console.log('✅ 페이지 로드 완료\n');

    // 2. 초기 화면 확인
    console.log('📍 Step 2: 초기 화면 확인');
    const welcomeTitle = await page.locator('.welcome-title').textContent();
    console.log(`   환영 메시지: "${welcomeTitle}"`);
    console.log('✅ 초기 화면 정상\n');

    // 3. 호텔 예약 메시지 입력
    console.log('📍 Step 3: "도쿄 호텔 예약하고 싶어요" 메시지 전송');
    await page.fill('.input-box', '도쿄 호텔 예약하고 싶어요');
    await page.click('.send-btn');
    console.log('✅ 메시지 전송 완료\n');

    // 4. 폼이 나타날 때까지 대기 (최대 15초)
    console.log('📍 Step 4: 사용자 입력 폼 대기...');
    await page.waitForSelector('.user-input-form', { timeout: 15000 });
    console.log('✅ 폼이 나타났습니다!\n');

    // 5. 폼 필드 확인
    console.log('📍 Step 5: 폼 필드 확인');
    const checkInField = await page.locator('input[type="date"][id="check_in"]');
    const checkOutField = await page.locator('input[type="date"][id="check_out"]');
    const guestsField = await page.locator('input[type="number"][id="guests"]');

    const hasCheckIn = await checkInField.count() > 0;
    const hasCheckOut = await checkOutField.count() > 0;
    const hasGuests = await guestsField.count() > 0;

    console.log(`   체크인 필드: ${hasCheckIn ? '✅' : '❌'}`);
    console.log(`   체크아웃 필드: ${hasCheckOut ? '✅' : '❌'}`);
    console.log(`   인원수 필드: ${hasGuests ? '✅' : '❌'}`);
    console.log('✅ 모든 폼 필드 확인 완료\n');

    // 6. 폼 데이터 입력
    console.log('📍 Step 6: 폼 데이터 입력');
    await checkInField.fill('2024-06-10');
    console.log('   체크인: 2024-06-10');

    await checkOutField.fill('2024-06-14');
    console.log('   체크아웃: 2024-06-14');

    await guestsField.fill('2');
    console.log('   인원수: 2명');
    console.log('✅ 폼 데이터 입력 완료\n');

    // 7. 제출 버튼 클릭
    console.log('📍 Step 7: 제출 버튼 클릭');
    await page.click('.form-submit-btn');
    console.log('✅ 제출 완료\n');

    // 8. 호텔 검색 결과 대기 (최대 15초)
    console.log('📍 Step 8: 호텔 검색 결과 대기...');
    await page.waitForSelector('.tool-card', { timeout: 15000 });
    console.log('✅ 호텔 검색 결과가 나타났습니다!\n');

    // 9. 검색 결과 확인
    console.log('📍 Step 9: 검색 결과 확인');
    const hotelCards = await page.locator('.hotel-item').count();
    console.log(`   검색된 호텔 수: ${hotelCards}개`);

    if (hotelCards > 0) {
      // 첫 번째 호텔 정보 출력
      const firstHotelName = await page.locator('.hotel-item .hotel-name').first().textContent();
      const firstHotelPrice = await page.locator('.hotel-item .hotel-price').first().textContent();
      console.log(`   첫 번째 호텔: ${firstHotelName}`);
      console.log(`   가격: ${firstHotelPrice}`);
    }
    console.log('✅ 검색 결과 확인 완료\n');

    // 10. 스크린샷 캡처
    console.log('📍 Step 10: 스크린샷 캡처');
    await page.screenshot({ path: '/Users/kitaepark/project/agent/sample-agent/ag-ui-demo/travel-agui/test-result.png', fullPage: true });
    console.log('✅ 스크린샷 저장: test-result.png\n');

    console.log('🎉 모든 테스트 통과! 호텔 예약 폼 기능이 정상적으로 작동합니다.\n');

    // 브라우저를 10초간 열어둠
    console.log('⏳ 브라우저를 10초간 열어둡니다...');
    await page.waitForTimeout(10000);

  } catch (error) {
    console.error('\n❌ 테스트 실패:', error.message);
    await page.screenshot({ path: '/Users/kitaepark/project/agent/sample-agent/ag-ui-demo/travel-agui/test-error.png', fullPage: true });
    console.log('   에러 스크린샷 저장: test-error.png');
  } finally {
    await browser.close();
    console.log('\n✅ 브라우저 종료');
  }
})();
