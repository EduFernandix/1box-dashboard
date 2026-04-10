const puppeteer = require('puppeteer');
const path = require('path');

const SCREENSHOT_DIR = 'temporary-screenshots';
const DEFAULT_URL = 'http://localhost:3000';

async function takeScreenshots(url = DEFAULT_URL) {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();

  // Desktop screenshots
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto(url, { waitUntil: 'networkidle0' });

  // Full page
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, 'full-page.png'),
    fullPage: true,
  });
  console.log('Captured: full-page.png');

  // Hero / above the fold
  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, 'hero.png'),
  });
  console.log('Captured: hero.png');

  // Scroll through sections
  const totalHeight = await page.evaluate(() => document.body.scrollHeight);
  const viewportHeight = 900;
  let section = 1;

  for (let y = viewportHeight; y < totalHeight; y += viewportHeight) {
    await page.evaluate((scrollY) => window.scrollTo(0, scrollY), y);
    await new Promise((r) => setTimeout(r, 500));
    const filename = `section-${section}.png`;
    await page.screenshot({
      path: path.join(SCREENSHOT_DIR, filename),
    });
    console.log(`Captured: ${filename}`);
    section++;
  }

  // Mobile screenshots
  await page.setViewport({ width: 375, height: 812 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await new Promise((r) => setTimeout(r, 500));

  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, 'mobile-hero.png'),
  });
  console.log('Captured: mobile-hero.png');

  await page.screenshot({
    path: path.join(SCREENSHOT_DIR, 'mobile-full.png'),
    fullPage: true,
  });
  console.log('Captured: mobile-full.png');

  await browser.close();
  console.log('\nAll screenshots saved to', SCREENSHOT_DIR);
}

// Allow passing URL as argument: node screenshot.js http://localhost:8080
const url = process.argv[2] || DEFAULT_URL;
takeScreenshots(url).catch(console.error);
