// 호텔 직접 검색 테스트 (모든 정보 포함)
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    await page.goto('http://localhost:5173');
    await page.waitForLoadState('networkidle');

    // 모든 정보가 포함된 호텔 검색
    console.log('검색: 도쿄 호텔 추천해줘 (6월 10일~14일, 2명)');
    await page.fill('.input-box', '도쿄 호텔 추천해줘 (6월 10일~14일, 2명)');
    await page.click('.send-btn');

    await page.waitForTimeout(10000);

    const hotelItems = await page.$$('.hotel-item');
    const hotelCards = await page.$$('.tool-card');

    console.log(`호텔 카드: ${hotelCards.length}`);
    console.log(`호텔 아이템: ${hotelItems.length}`);

    if (hotelItems.length > 0) {
      console.log('✅ 호텔 결과 표시됨!');
    } else {
      console.log('❌ 호텔 결과 없음');
    }

    await page.screenshot({ path: 'test-hotel-direct.png', fullPage: true });
    await page.waitForTimeout(5000);

  } catch (error) {
    console.error('에러:', error.message);
  } finally {
    await browser.close();
  }
})();
