const puppeteer = require('puppeteer');
(async () => {
    const browser = await puppeteer.launch({ headless: 'new' });
    const page = await browser.newPage();

    // Block API calls so we see the loader
    await page.setRequestInterception(true);
    page.on('request', req => {
        if (req.url().includes('/api/ga4/')) {
            // Delay response to capture loading state
            setTimeout(() => req.abort(), 5000);
        } else {
            req.continue();
        }
    });

    await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle0' });
    const btns = await page.$$('.nav-btn');

    // Marketing loader
    await btns[2].click();
    await new Promise(r => setTimeout(r, 800));
    await page.screenshot({ path: 'temporary-screenshots/loader-marketing.png' });
    console.log('Marketing loader captured');

    // Funnel loader
    await btns[3].click();
    await new Promise(r => setTimeout(r, 800));
    await page.screenshot({ path: 'temporary-screenshots/loader-funnel.png' });
    console.log('Funnel loader captured');

    // Weekly loader
    await btns[4].click();
    await new Promise(r => setTimeout(r, 800));
    await page.screenshot({ path: 'temporary-screenshots/loader-weekly.png' });
    console.log('Weekly loader captured');

    await browser.close();
    console.log('Done');
})();
