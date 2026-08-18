const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1400, height: 900 } });
  const errs = [];
  p.on('console', m => m.type()==='error' && errs.push(m.text()));

  // 1. no run + direct /results  -> should bounce to setup
  await p.goto('http://localhost:5173/results', { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(1500);
  console.log('guard /results with no run -> URL:', new URL(p.url()).pathname);

  // 2. seed a real completed run id, reload, confirm it rehydrates
  const rid = process.argv[2];
  await p.evaluate((id) => localStorage.setItem('cv-screener:run',
      JSON.stringify({ runId: id, status: 'completed', totalCvs: 200, processedCvs: 200 })), rid);
  await p.goto('http://localhost:5173/results', { waitUntil: 'domcontentloaded' });
  await p.waitForTimeout(3000);
  console.log('after refresh with stored run -> URL:', new URL(p.url()).pathname);
  const cards = await p.locator('article').count();
  const heading = await p.locator('h1').first().innerText().catch(()=> '');
  console.log('cards rendered after refresh:', cards, '| heading:', heading);
  const backBtn = await p.getByText('New screening').count();
  console.log('back button present:', backBtn > 0);

  // 3. click back -> clears storage, returns to setup
  if (backBtn) {
    await p.getByText('New screening').click();
    await p.waitForTimeout(1200);
    const stored = await p.evaluate(() => localStorage.getItem('cv-screener:run'));
    console.log('after back -> URL:', new URL(p.url()).pathname, '| storage cleared:', stored === null);
  }
  console.log('console errors:', errs.filter(e=>!e.includes('DevTools')).length);
  await b.close();
})();
