# 1Box Dashboard

## Screenshot Workflow

When building or modifying frontend pages, use Puppeteer to visually review your work:

1. Start a local server: `npx serve . -l 3000`
2. Use Puppeteer to take screenshots at different scroll positions
3. Save screenshots to `temporary-screenshots/` folder
4. Review each screenshot and identify visual issues
5. Fix issues and re-screenshot to verify
6. Do at least 2 passes of screenshot review and polish

### Taking Screenshots

```js
const puppeteer = require('puppeteer');

async function takeScreenshots(url) {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();

  // Desktop viewport
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto(url, { waitUntil: 'networkidle0' });

  // Full page
  await page.screenshot({ path: 'temporary-screenshots/full-page.png', fullPage: true });

  // Hero/above the fold
  await page.screenshot({ path: 'temporary-screenshots/hero.png' });

  // Scroll through sections
  const totalHeight = await page.evaluate(() => document.body.scrollHeight);
  const viewportHeight = 900;
  let section = 1;

  for (let y = viewportHeight; y < totalHeight; y += viewportHeight) {
    await page.evaluate((scrollY) => window.scrollTo(0, scrollY), y);
    await new Promise(r => setTimeout(r, 500));
    await page.screenshot({ path: `temporary-screenshots/section-${section}.png` });
    section++;
  }

  // Mobile viewport
  await page.setViewport({ width: 375, height: 812 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await new Promise(r => setTimeout(r, 500));
  await page.screenshot({ path: 'temporary-screenshots/mobile-hero.png' });
  await page.screenshot({ path: 'temporary-screenshots/mobile-full.png', fullPage: true });

  await browser.close();
}
```

### Screenshotting External Websites for Inspiration

To clone or use a website as design reference:
1. Screenshot the target URL using the same Puppeteer approach
2. Review the screenshots to understand layout, colors, typography
3. Build the page using those screenshots as visual reference
4. Use the screenshot loop to compare your output against the reference

## Tech Stack
- Frontend: HTML/CSS/JS (single page)
- Use the `/frontend-design` skill for high-quality UI work
