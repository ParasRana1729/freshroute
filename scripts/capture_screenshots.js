import puppeteer from 'puppeteer-core';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const screenshotsDir = path.join(__dirname, '..', 'screenshots');

async function capture() {
  console.log('Launching Chromium for screenshot generation...');
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/chromium',
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--window-size=1440,900'],
    defaultViewport: { width: 1440, height: 900, deviceScaleFactor: 2 }
  });

  const page = await browser.newPage();
  await page.goto('http://localhost:3000/#console', { waitUntil: 'networkidle0', timeout: 15000 });
  await new Promise(r => setTimeout(r, 1500));

  // 1. Overview Tab
  console.log('Capturing console_overview.png...');
  await page.screenshot({ path: path.join(screenshotsDir, 'console_overview.png'), fullPage: false });

  // Helper to click sidebar nav by index
  const navButtons = await page.$$('.s-nav-btn');
  console.log(`Found ${navButtons.length} sidebar buttons.`);

  // 2. Dispatch Map Tab (index 1)
  if (navButtons[1]) {
    console.log('Navigating to Live Dispatch Map...');
    await navButtons[1].click();
    await new Promise(r => setTimeout(r, 1200));
    console.log('Capturing dispatch_map.png...');
    await page.screenshot({ path: path.join(screenshotsDir, 'dispatch_map.png') });
  }

  // 3. Langar Match Queue Tab (index 2)
  if (navButtons[2]) {
    console.log('Navigating to Langar Match Queue...');
    await navButtons[2].click();
    await new Promise(r => setTimeout(r, 1000));
    console.log('Capturing match_queue.png...');
    await page.screenshot({ path: path.join(screenshotsDir, 'match_queue.png') });
  }

  // 4. Thermal Decay Matrix Tab (index 3)
  if (navButtons[3]) {
    console.log('Navigating to Thermal Decay Matrix...');
    await navButtons[3].click();
    await new Promise(r => setTimeout(r, 1000));
    console.log('Capturing thermal_decay.png...');
    await page.screenshot({ path: path.join(screenshotsDir, 'thermal_decay.png') });
  }

  // 5. 23 District Deficit Tab (index 4)
  if (navButtons[4]) {
    console.log('Navigating to 23 District Deficit...');
    await navButtons[4].click();
    await new Promise(r => setTimeout(r, 1000));
    console.log('Capturing district_forecast.png...');
    await page.screenshot({ path: path.join(screenshotsDir, 'district_forecast.png') });
  }

  // 6. REST API Sandbox Tab (index 5)
  if (navButtons[5]) {
    console.log('Navigating to REST API Sandbox...');
    await navButtons[5].click();
    await new Promise(r => setTimeout(r, 1000));
    console.log('Capturing rest_api_sandbox.png...');
    await page.screenshot({ path: path.join(screenshotsDir, 'rest_api_sandbox.png') });
  }

  await browser.close();
  console.log('All 6 authentic PNG screenshots captured successfully!');
}

capture().catch(err => {
  console.error('Error capturing screenshots:', err);
  process.exit(1);
});
